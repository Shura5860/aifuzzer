//! MAP-Elites (Quality-Diversity) Izgara Modülü
//!
//! Izgara Boyutları (3D - 45 Niş):
//! 1. Mutatör Türü (5): Lexical, Encoding, Placement, Crossover, Baseline
//! 2. Uzunluk Sınıfı (3): Short (<100 char), Medium (100-300 char), Long (>300 char)
//! 3. Savunma Katmanı (3): Zero (0 tetikleme), Single (1 tetikleme), Multi (2+ tetikleme)

use crate::corpus::SeedRecord;
use std::collections::HashMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MutatorFamily {
    Baseline,
    Lexical,
    Encoding,
    Placement,
    Crossover,
    Semantic,
}

impl MutatorFamily {
    pub fn from_name(name: Option<&str>) -> Self {
        match name {
            Some(n) if n.starts_with("lexical::") => MutatorFamily::Lexical,
            Some(n) if n.starts_with("encoding::") => MutatorFamily::Encoding,
            Some(n) if n.starts_with("placement::") => MutatorFamily::Placement,
            Some(n) if n.starts_with("crossover") => MutatorFamily::Crossover,
            Some(n) if n.starts_with("semantic::") => MutatorFamily::Semantic,
            _ => MutatorFamily::Baseline,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum LengthBucket {
    Short,  // < 100 char
    Medium, // 100 - 300 char
    Long,   // > 300 char
}

impl LengthBucket {
    pub fn from_len(len: usize) -> Self {
        if len < 100 {
            LengthBucket::Short
        } else if len <= 300 {
            LengthBucket::Medium
        } else {
            LengthBucket::Long
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DefenseLayerBucket {
    Zero,   // 0 katman (radar altı)
    Single, // 1 katman (near-miss)
    Multi,  // 2+ katman (yoğun tetikleme)
}

impl DefenseLayerBucket {
    pub fn from_count(count: usize) -> Self {
        match count {
            0 => DefenseLayerBucket::Zero,
            1 => DefenseLayerBucket::Single,
            _ => DefenseLayerBucket::Multi,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct NicheKey {
    pub family: MutatorFamily,
    pub length: LengthBucket,
    pub defense: DefenseLayerBucket,
}

#[derive(Debug, Clone)]
pub struct EliteEntry {
    pub seed: SeedRecord,
    pub fitness: f64,
    pub evaluation_count: usize,
}

pub struct MapElitesGrid {
    grid: HashMap<NicheKey, EliteEntry>,
    total_niches: usize,
}

impl Default for MapElitesGrid {
    fn default() -> Self {
        Self::new()
    }
}

impl MapElitesGrid {
    pub fn new() -> Self {
        // 6 (family) * 3 (length) * 3 (defense) = 54 toplam niş
        Self {
            grid: HashMap::new(),
            total_niches: 54,
        }
    }

    pub fn compute_niche_key(&self, seed: &SeedRecord) -> NicheKey {
        NicheKey {
            family: MutatorFamily::from_name(seed.mutator_applied.as_deref()),
            length: LengthBucket::from_len(seed.prompt.len()),
            defense: DefenseLayerBucket::from_count(seed.triggered_layers.len()),
        }
    }

    /// Yeni tohumu ilgili nişe yerleştirmeyi dener.
    /// Eğer niş boşsa veya yeni tohum mevcut elit tohumdan daha yüksek fitness'a sahipse
    /// elit tohum güncellenir ve true döner (yeni elit / niş keşfi).
    pub fn insert_or_update(&mut self, seed: SeedRecord) -> bool {
        let key = self.compute_niche_key(&seed);
        let fitness = seed.fitness_score;

        match self.grid.get_mut(&key) {
            Some(existing) => {
                if fitness > existing.fitness {
                    existing.seed = seed;
                    existing.fitness = fitness;
                    existing.evaluation_count += 1;
                    true
                } else {
                    existing.evaluation_count += 1;
                    false
                }
            }
            None => {
                self.grid.insert(
                    key,
                    EliteEntry {
                        seed,
                        fitness,
                        evaluation_count: 1,
                    },
                );
                true
            }
        }
    }

    pub fn occupied_niches_count(&self) -> usize {
        self.grid.len()
    }

    pub fn coverage_ratio(&self) -> f64 {
        (self.grid.len() as f64) / (self.total_niches as f64)
    }

    pub fn get_all_elites(&self) -> Vec<SeedRecord> {
        self.grid.values().map(|e| e.seed.clone()).collect()
    }
}
