//! AIFuzzer Modüler Mutatör Motoru

pub mod advanced;
pub mod crossover;
pub mod encoding;
pub mod lexical;
pub mod placement;
pub mod semantic;

use rand::prelude::*;
use std::sync::Arc;

/// Herhangi bir mutasyon stratejisinin sağlaması gereken ortak arayüz (Lego bloğu).
pub trait Mutator: Send + Sync {
    /// Mutatörün adı (ör: "lexical::homoglyph", "encoding::base64")
    fn name(&self) -> &'static str;

    /// Verilen metni dönüştürerek mutasyona uğratır.
    fn mutate(&self, input: &str) -> String;
}

pub struct MutatorPool {
    mutators: Vec<Arc<dyn Mutator>>,
    /// Multi-Armed Bandit (MAB): Her mutatörün kaç kez çekildiği (pulls)
    pull_counts: Vec<usize>,
    /// Multi-Armed Bandit (MAB): Her mutatörün kazandırdığı toplam ödül (fitness artışı & bypass)
    reward_scores: Vec<f64>,
}

impl Default for MutatorPool {
    fn default() -> Self {
        Self::new()
    }
}

impl MutatorPool {
    pub fn new() -> Self {
        Self {
            mutators: Vec::new(),
            pull_counts: Vec::new(),
            reward_scores: Vec::new(),
        }
    }

    pub fn register(&mut self, mutator: impl Mutator + 'static) {
        self.mutators.push(Arc::new(mutator));
        self.pull_counts.push(1); // Sıfıra bölmeyi önlemek için başlangıç 1
        self.reward_scores.push(1.0); // Başlangıç eşit öncelik ödülü
    }

    pub fn default_pool() -> Self {
        let mut pool = Self::new();
        // Sözcüksel (Lexical)
        pool.register(lexical::CaseToggleMutator);
        pool.register(lexical::ZeroWidthInjector);
        pool.register(lexical::HomoglyphMutator);
        pool.register(lexical::WhitespaceMutator);

        // Kodlama (Encoding)
        pool.register(encoding::Base64Mutator);
        pool.register(encoding::Rot13Mutator);
        pool.register(encoding::LeetspeakMutator);
        pool.register(encoding::MarkdownWrapMutator);

        // Konum & Çerçeveleme (Placement)
        pool.register(placement::DelimeterWrapMutator);
        pool.register(placement::SystemPromptInfixMutator);

        // İleri Düzey Saldırı Kütüphanesi (Advanced Attack Zoo)
        pool.register(advanced::AsciiArtMutator);
        pool.register(advanced::ManyShotMutator::default());
        pool.register(advanced::TokenGlitchMutator);

        pool
    }

    pub fn select_random(&self) -> Option<Arc<dyn Mutator>> {
        if self.mutators.is_empty() {
            return None;
        }
        let mut rng = thread_rng();
        self.mutators.choose(&mut rng).cloned()
    }

    /// Multi-Armed Bandit (UCB1 / Epsilon-Greedy esintili) Adaptif Seçim:
    /// Başarılı mutatörlerin seçilme olasılığını dinamik olarak artırır (%85 sömürü, %15 keşif).
    pub fn select_adaptive(&mut self) -> Option<(usize, Arc<dyn Mutator>)> {
        if self.mutators.is_empty() {
            return None;
        }

        let mut rng = thread_rng();
        let total_mutators = self.mutators.len();

        // %15 Epsilon-Greedy Keşif (Exploration): Rastgele dene
        if rng.gen_bool(0.15) {
            let idx = rng.gen_range(0..total_mutators);
            self.pull_counts[idx] += 1;
            return Some((idx, self.mutators[idx].clone()));
        }

        // %85 Sömürü (Exploitation): Ortalama ödülü en yüksek olanı ağırlıklı seç
        let weights: Vec<f64> = self
            .reward_scores
            .iter()
            .zip(self.pull_counts.iter())
            .map(|(&r, &c)| (r / (c as f64)).max(0.05))
            .collect();

        // Normalizasyon ve rulet çarkı seçimi
        let total_weight: f64 = weights.iter().sum();
        if total_weight <= 0.0 {
            let idx = rng.gen_range(0..total_mutators);
            self.pull_counts[idx] += 1;
            return Some((idx, self.mutators[idx].clone()));
        }

        let mut pick = rng.gen_range(0.0..total_weight);
        let mut selected_idx = 0;
        for (i, &w) in weights.iter().enumerate() {
            if pick <= w {
                selected_idx = i;
                break;
            }
            pick -= w;
        }

        self.pull_counts[selected_idx] += 1;
        Some((selected_idx, self.mutators[selected_idx].clone()))
    }

    /// Mutatörün başarısına göre MAB ödülünü günceller (Bypass: +10.0, Yeni Niş/Fitness: +2.0)
    pub fn feedback_reward(&mut self, mutator_idx: usize, reward: f64) {
        if mutator_idx < self.reward_scores.len() {
            self.reward_scores[mutator_idx] += reward;
        }
    }

    pub fn len(&self) -> usize {
        self.mutators.len()
    }

    pub fn is_empty(&self) -> bool {
        self.mutators.is_empty()
    }
}
