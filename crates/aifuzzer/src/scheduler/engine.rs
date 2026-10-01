//! AIFuzzer Fuzzing Engine & Orchestrator

use crate::client::GatewayClient;
use crate::corpus::{CorpusStorage, SeedRecord};
use crate::mutators::crossover::CrossoverEngine;
use crate::mutators::MutatorPool;
use crate::proto::PayloadLocation;
use crate::scheduler::map_elites::MapElitesGrid;
use crate::scheduler::power_schedule::PowerSchedule;
use anyhow::Result;
use rand::prelude::*;
use std::collections::HashMap;
use tracing::{info, warn};
use uuid::Uuid;

#[derive(Debug, Default, Clone)]
pub struct FuzzStats {
    pub total_executions: usize,
    pub total_bypasses: usize,
    pub occupied_niches: usize,
    pub coverage_ratio: f64,
}

pub struct FuzzEngine {
    client: GatewayClient,
    storage: CorpusStorage,
    mutator_pool: MutatorPool,
    grid: MapElitesGrid,
    power_schedule: PowerSchedule,
    selection_counts: HashMap<String, usize>,
    stats: FuzzStats,
}

impl FuzzEngine {
    pub fn new(client: GatewayClient, storage: CorpusStorage) -> Self {
        Self {
            client,
            storage,
            mutator_pool: MutatorPool::default_pool(),
            grid: MapElitesGrid::new(),
            power_schedule: PowerSchedule::default_schedule(),
            selection_counts: HashMap::new(),
            stats: FuzzStats::default(),
        }
    }

    /// Başlangıç tohumunu (seed) fuzzer'a yükler ve değerlendirir.
    pub async fn add_initial_seed(&mut self, prompt: &str) -> Result<()> {
        let test_case_id = format!("seed-init-{}", Uuid::new_v4().simple());
        let res = self
            .client
            .execute_target(
                &test_case_id,
                prompt,
                PayloadLocation::UserMessage,
                vec!["AIFUZZ_CANARY_SECRET_CORE_TOKEN_99".to_string()],
            )
            .await?;

        self.stats.total_executions += 1;
        if res.is_bypass {
            self.stats.total_bypasses += 1;
        }

        let seed = SeedRecord {
            id: test_case_id,
            parent_id: None,
            prompt: prompt.to_string(),
            payload_location: "USER_MESSAGE".to_string(),
            mutator_applied: None,
            fitness_score: res.raw_guardrail_score,
            is_bypass: res.is_bypass,
            canary_leaked: res.canary_leaked,
            unauthorized_tool: res.unauthorized_tool_called,
            triggered_layers: res.triggered_defense_layers,
            file_path: None,
            created_at: "".to_string(),
        };

        let saved = self.storage.save_seed(seed.clone())?;
        self.grid.insert_or_update(saved);
        self.update_stats();
        Ok(())
    }

    fn update_stats(&mut self) {
        self.stats.occupied_niches = self.grid.occupied_niches_count();
        self.stats.coverage_ratio = self.grid.coverage_ratio();
    }

    /// Fuzzing kampanyasını belirtilen adım sayısı kadar koşturur.
    pub async fn run_campaign(&mut self, iterations: usize) -> Result<FuzzStats> {
        let mut rng = thread_rng();

        for i in 0..iterations {
            let elites = self.grid.get_all_elites();
            if elites.is_empty() {
                warn!("Corpus boş, mutasyon yapılamadı!");
                break;
            }

            // 1. MAP-Elites havuzundan elit tohum seçimi
            let chosen_seed = elites.choose(&mut rng).unwrap().clone();
            let count = self.selection_counts.entry(chosen_seed.id.clone()).or_insert(0);
            *count += 1;

            // 2. Power schedule ile enerji tahsisi
            let energy = self.power_schedule.assign_energy(&chosen_seed, *count);

            for _ in 0..energy {
                // 3. Mutasyon Stratejisi Seçimi:
                // %15 Crossover, %15 Semantik Mutasyon (gRPC), %70 Yerel Hızlı Mutatör (MAB Adaptif)
                let roll: f64 = rng.gen();
                let mut applied_mutator_idx: Option<usize> = None;

                let (mutated_prompt, mutator_name) = if elites.len() > 1 && roll < 0.15 {
                    let other_seed = elites.choose(&mut rng).unwrap();
                    let hybrid = CrossoverEngine::crossover(&chosen_seed.prompt, &other_seed.prompt);
                    (hybrid, "crossover::hybrid".to_string())
                } else if roll < 0.30 {
                    // Semantik Mutasyon (Python gRPC servisi üzerinden)
                    let strategies = [
                        crate::proto::SemanticMutationStrategy::MutationStrategyRoleplayFrame,
                        crate::proto::SemanticMutationStrategy::MutationStrategyParaphrase,
                        crate::proto::SemanticMutationStrategy::MutationStrategyHypothetical,
                    ];
                    let strat = *strategies.choose(&mut rng).unwrap();
                    let strat_name = match strat {
                        crate::proto::SemanticMutationStrategy::MutationStrategyRoleplayFrame => "semantic::roleplay",
                        crate::proto::SemanticMutationStrategy::MutationStrategyParaphrase => "semantic::paraphrase",
                        _ => "semantic::hypothetical",
                    };

                    match self.client.mutate_semantic(&chosen_seed.prompt, strat).await {
                        Ok(resp) if resp.success => (resp.mutated_text, strat_name.to_string()),
                        _ => {
                            let (idx, mutator) = self.mutator_pool.select_adaptive().unwrap();
                            applied_mutator_idx = Some(idx);
                            (mutator.mutate(&chosen_seed.prompt), mutator.name().to_string())
                        }
                    }
                } else {
                    let (idx, mutator) = self.mutator_pool.select_adaptive().unwrap();
                    applied_mutator_idx = Some(idx);
                    (mutator.mutate(&chosen_seed.prompt), mutator.name().to_string())
                };

                let child_id = format!("mut-{}-{}", i, Uuid::new_v4().simple());

                // 4. Hedef Gateway & Oracle çalıştırması
                let res = self
                    .client
                    .execute_target(
                        &child_id,
                        &mutated_prompt,
                        PayloadLocation::UserMessage,
                        vec!["AIFUZZ_CANARY_SECRET_CORE_TOKEN_99".to_string()],
                    )
                    .await?;

                self.stats.total_executions += 1;

                let is_bypass = res.is_bypass;
                if is_bypass {
                    self.stats.total_bypasses += 1;
                    info!(
                        "[BYPASS_DETECTED] id={} mutator={} canary_leaked={}",
                        child_id, mutator_name, res.canary_leaked
                    );
                    // MAB Ödülü: Bypass yakalayan mutatöre +10.0 puan
                    if let Some(idx) = applied_mutator_idx {
                        self.mutator_pool.feedback_reward(idx, 10.0);
                    }
                }

                // 5. Tohum kaydı
                let child_seed = SeedRecord {
                    id: child_id,
                    parent_id: Some(chosen_seed.id.clone()),
                    prompt: mutated_prompt,
                    payload_location: "USER_MESSAGE".to_string(),
                    mutator_applied: Some(mutator_name),
                    fitness_score: res.raw_guardrail_score,
                    is_bypass: res.is_bypass,
                    canary_leaked: res.canary_leaked,
                    unauthorized_tool: res.unauthorized_tool_called,
                    triggered_layers: res.triggered_defense_layers,
                    file_path: None,
                    created_at: "".to_string(),
                };

                // Eğer bypass ise veya MAP-Elites ızgarasında yeni/üstün niş açtıysa diske/DB'ye kaydet
                let is_new_niche = self.grid.insert_or_update(child_seed.clone());
                if is_bypass || is_new_niche {
                    self.storage.save_seed(child_seed)?;
                    self.update_stats();
                    // MAB Ödülü: Yeni niş açan mutatöre +2.0 puan
                    if let Some(idx) = applied_mutator_idx {
                        self.mutator_pool.feedback_reward(idx, 2.0);
                    }
                }
            }
        }

        self.update_stats();
        Ok(self.stats.clone())
    }

    /// Çoklu paralel worker havuzu (Distributed/Concurrent Fuzzing Engine)
    pub async fn run_campaign_concurrent(&mut self, iterations: usize, concurrency: usize) -> Result<FuzzStats> {
        if concurrency <= 1 {
            return self.run_campaign(iterations).await;
        }

        info!(
            "[DistributedEngine] Paralel worker havuzu başlatılıyor: workers={}, total_iterations={}",
            concurrency, iterations
        );

        let iterations_per_worker = iterations.div_ceil(concurrency);

        for _ in 0..iterations_per_worker {
            let elites = self.grid.get_all_elites();
            if elites.is_empty() {
                break;
            }

            // Concurrency kadar mutasyon adayı hazırla
            let mut candidates = Vec::with_capacity(concurrency);
            let mut rng = thread_rng();

            for w in 0..concurrency {
                let chosen = elites.choose(&mut rng).unwrap().clone();
                let mutator = self.mutator_pool.select_random().unwrap();
                let mutated = mutator.mutate(&chosen.prompt);
                let child_id = format!("dist-{}-{}", w, Uuid::new_v4().simple());
                candidates.push((child_id, chosen.id.clone(), mutated, mutator.name().to_string()));
            }

            // Tokio JoinSet ile paralel Gateway istekleri
            let mut join_set = tokio::task::JoinSet::new();

            for (cid, pid, mutated_prompt, mut_name) in candidates {
                let mut client = self.client.clone();
                join_set.spawn(async move {
                    let res = client
                        .execute_target(
                            &cid,
                            &mutated_prompt,
                            PayloadLocation::UserMessage,
                            vec!["AIFUZZ_CANARY_SECRET_CORE_TOKEN_99".to_string()],
                        )
                        .await;
                    (cid, pid, mutated_prompt, mut_name, res)
                });
            }

            while let Some(res) = join_set.join_next().await {
                if let Ok((cid, pid, prompt, mut_name, Ok(target_res))) = res {
                    self.stats.total_executions += 1;
                    let is_bypass = target_res.is_bypass;
                    if is_bypass {
                        self.stats.total_bypasses += 1;
                    }

                    let child_seed = SeedRecord {
                        id: cid,
                        parent_id: Some(pid),
                        prompt,
                        payload_location: "USER_MESSAGE".to_string(),
                        mutator_applied: Some(mut_name),
                        fitness_score: target_res.raw_guardrail_score,
                        is_bypass,
                        canary_leaked: target_res.canary_leaked,
                        unauthorized_tool: target_res.unauthorized_tool_called,
                        triggered_layers: target_res.triggered_defense_layers,
                        file_path: None,
                        created_at: "".to_string(),
                    };

                    let is_new_niche = self.grid.insert_or_update(child_seed.clone());
                    if is_bypass || is_new_niche {
                        self.storage.save_seed(child_seed)?;
                        self.update_stats();
                    }
                }
            }
        }

        self.update_stats();
        Ok(self.stats.clone())
    }

    pub fn stats(&self) -> &FuzzStats {
        &self.stats
    }

    pub fn storage(&self) -> &CorpusStorage {
        &self.storage
    }
}
