//! Karakter / Bayt Seviyesinde Delta Debugging (DDmin) ve Doğrulama Modülü

use crate::client::GatewayClient;
use crate::proto::PayloadLocation;
use anyhow::Result;
use std::fs;
use std::path::{Path, PathBuf};
use tracing::info;

pub struct Minimizer {
    client: GatewayClient,
    minimized_dir: PathBuf,
    expected_canaries: Vec<String>,
}

impl Minimizer {
    pub fn new<P: AsRef<Path>>(
        client: GatewayClient,
        minimized_dir: P,
        expected_canaries: Vec<String>,
    ) -> Result<Self> {
        let path = minimized_dir.as_ref().to_path_buf();
        fs::create_dir_all(&path)?;
        Ok(Self {
            client,
            minimized_dir: path,
            expected_canaries,
        })
    }

    /// Flaky/rastgele çıktıları elemek için adayı 3 kez ardışık test eder.
    pub async fn verify_reproducibility(&mut self, prompt: &str) -> Result<bool> {
        for i in 0..3 {
            let tc_id = format!("verify-{}", i);
            let res = self
                .client
                .execute_target(
                    &tc_id,
                    prompt,
                    PayloadLocation::UserMessage,
                    self.expected_canaries.clone(),
                )
                .await?;

            if !res.is_bypass {
                return Ok(false);
            }
        }
        Ok(true)
    }

    /// Verilen metnin hala bypass üretip üretmediğini sorgular.
    async fn test_bypass(&mut self, prompt: &str) -> bool {
        if prompt.trim().is_empty() {
            return false;
        }
        match self
            .client
            .execute_target(
                "ddmin-eval",
                prompt,
                PayloadLocation::UserMessage,
                self.expected_canaries.clone(),
            )
            .await
        {
            Ok(res) => res.is_bypass,
            Err(_) => false,
        }
    }

    /// Zeller'ın Klasik Karakter / Bayt Seviyesi DDmin Algoritması
    pub async fn minimize(&mut self, initial_prompt: &str) -> Result<String> {
        let initial_chars: Vec<char> = initial_prompt.chars().collect();
        let initial_len = initial_chars.len();

        info!(
            "[DDmin] Başlatılıyor: Orijinal uzunluk {} karakter...",
            initial_len
        );

        let mut current_chars = initial_chars;
        let mut granularity = 2;

        while current_chars.len() >= 2 {
            let n = granularity;
            let len = current_chars.len();
            let chunk_size = len.div_ceil(n);
            let mut reduced = false;

            // 1. Alt parçalardan birini tek başına dene (parçalardan biri tek başına yeterli mi?)
            for i in 0..n {
                let start = i * chunk_size;
                if start >= len {
                    break;
                }
                let end = (start + chunk_size).min(len);
                let candidate: String = current_chars[start..end].iter().collect();

                if self.test_bypass(&candidate).await {
                    current_chars = candidate.chars().collect();
                    granularity = 2.max(granularity - 1);
                    reduced = true;
                    break;
                }
            }

            if reduced {
                continue;
            }

            // 2. Alt parçalardan birini çıkarıp kalan kısmı dene (parça gereksiz mi?)
            for i in 0..n {
                let start = i * chunk_size;
                if start >= len {
                    break;
                }
                let end = (start + chunk_size).min(len);

                let mut complement = Vec::with_capacity(len - (end - start));
                complement.extend_from_slice(&current_chars[..start]);
                complement.extend_from_slice(&current_chars[end..]);

                let candidate: String = complement.iter().collect();

                if self.test_bypass(&candidate).await {
                    current_chars = complement;
                    granularity = 2.max(granularity - 1);
                    reduced = true;
                    break;
                }
            }

            if !reduced {
                if granularity >= current_chars.len() {
                    break; // Daha fazla küçültülemez (1 karakterlik bloklar da denendi)
                }
                granularity = (granularity * 2).min(current_chars.len());
            }
        }

        let minimized: String = current_chars.into_iter().collect();
        info!(
            "[DDmin] Tamamlandı: {} -> {} karakter (%{:.1} küçülme)",
            initial_len,
            minimized.len(),
            (1.0 - (minimized.len() as f64 / initial_len as f64)) * 100.0
        );

        Ok(minimized)
    }

    /// Minimize edilen bypass'ı diske minimal PoC olarak kaydeder.
    pub fn save_minimized_poc(&self, id: &str, minimized_prompt: &str) -> Result<PathBuf> {
        let file_path = self.minimized_dir.join(format!("poc_min_{}.txt", id));
        fs::write(&file_path, minimized_prompt)?;
        Ok(file_path)
    }
}
