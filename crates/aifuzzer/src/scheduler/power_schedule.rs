//! AFL Fast Tarzı Enerji ve Zamanlama Hesaplayıcı

use crate::corpus::SeedRecord;

pub struct PowerSchedule {
    base_energy: usize,
    max_energy: usize,
}

impl PowerSchedule {
    pub fn new(base_energy: usize, max_energy: usize) -> Self {
        Self {
            base_energy,
            max_energy,
        }
    }

    pub fn default_schedule() -> Self {
        Self {
            base_energy: 4,
            max_energy: 32,
        }
    }

    /// Tohumun fitness'ına ve daha önce kaç kez seçildiğine göre mutasyon döngüsü (enerji) hesaplar.
    pub fn assign_energy(&self, seed: &SeedRecord, selection_count: usize) -> usize {
        let fitness = seed.fitness_score.clamp(0.0, 1.0);

        // 1. Fitness çarpanı: [1.0 - 4.0]
        let fitness_factor = 1.0 + (fitness * 3.0);

        // 2. AFL Fast sönümleme: Çok seçilmiş tohumların enerjisini normalize et
        let count_dampening = 1.0 / ((selection_count + 1) as f64).sqrt();

        // 3. Nihai enerji
        let calculated = (self.base_energy as f64 * fitness_factor * count_dampening).round() as usize;

        // Taban enerjiden az olamaz, tavan enerjiyi geçemez
        calculated.clamp(1, self.max_energy)
    }
}
