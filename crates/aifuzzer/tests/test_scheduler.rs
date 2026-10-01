//! MAP-Elites ve Power Schedule Birim Testleri

use aifuzzer::corpus::SeedRecord;
use aifuzzer::scheduler::map_elites::{DefenseLayerBucket, LengthBucket, MapElitesGrid, MutatorFamily};
use aifuzzer::scheduler::power_schedule::PowerSchedule;

#[test]
fn test_map_elites_niche_computation() {
    let grid = MapElitesGrid::new();

    let seed1 = SeedRecord {
        id: "s1".into(),
        parent_id: None,
        prompt: "Short prompt".into(), // < 100 char => Short
        payload_location: "USER_MESSAGE".into(),
        mutator_applied: Some("lexical::homoglyph".into()), // Lexical
        fitness_score: 0.5,
        is_bypass: false,
        canary_leaked: false,
        unauthorized_tool: false,
        triggered_layers: vec![], // Zero
        file_path: None,
        created_at: "".into(),
    };

    let key = grid.compute_niche_key(&seed1);
    assert_eq!(key.family, MutatorFamily::Lexical);
    assert_eq!(key.length, LengthBucket::Short);
    assert_eq!(key.defense, DefenseLayerBucket::Zero);
}

#[test]
fn test_map_elites_quality_diversity_competition() {
    let mut grid = MapElitesGrid::new();

    // 1. Düşük fitness'lı tohum nişe eklenir
    let seed_low = SeedRecord {
        id: "low".into(),
        parent_id: None,
        prompt: "base64 sample text".into(),
        payload_location: "USER_MESSAGE".into(),
        mutator_applied: Some("encoding::base64_wrap".into()),
        fitness_score: 0.3,
        is_bypass: false,
        canary_leaked: false,
        unauthorized_tool: false,
        triggered_layers: vec!["L1".into()],
        file_path: None,
        created_at: "".into(),
    };

    let inserted = grid.insert_or_update(seed_low);
    assert!(inserted);
    assert_eq!(grid.occupied_niches_count(), 1);

    // 2. Aynı nişe daha yüksek fitness'lı tohum gelir: Elit güncellenmeli!
    let seed_high = SeedRecord {
        id: "high".into(),
        parent_id: None,
        prompt: "base64 sample text better".into(),
        payload_location: "USER_MESSAGE".into(),
        mutator_applied: Some("encoding::base64_wrap".into()),
        fitness_score: 0.85,
        is_bypass: false,
        canary_leaked: false,
        unauthorized_tool: false,
        triggered_layers: vec!["L1".into()],
        file_path: None,
        created_at: "".into(),
    };

    let updated = grid.insert_or_update(seed_high);
    assert!(updated);
    assert_eq!(grid.occupied_niches_count(), 1); // Niş sayısı değişmez, elit güncellenir

    // 3. Aynı nişe daha düşük fitness'lı tohum gelir: Reddedilmeli!
    let seed_inferior = SeedRecord {
        id: "inferior".into(),
        parent_id: None,
        prompt: "base64 sample text worse".into(),
        payload_location: "USER_MESSAGE".into(),
        mutator_applied: Some("encoding::base64_wrap".into()),
        fitness_score: 0.4,
        is_bypass: false,
        canary_leaked: false,
        unauthorized_tool: false,
        triggered_layers: vec!["L1".into()],
        file_path: None,
        created_at: "".into(),
    };

    let rejected = grid.insert_or_update(seed_inferior);
    assert!(!rejected);
}

#[test]
fn test_power_schedule_allocation() {
    let scheduler = PowerSchedule::default_schedule();

    let high_fitness_seed = SeedRecord {
        id: "h".into(),
        parent_id: None,
        prompt: "test".into(),
        payload_location: "".into(),
        mutator_applied: None,
        fitness_score: 0.95,
        is_bypass: false,
        canary_leaked: false,
        unauthorized_tool: false,
        triggered_layers: vec![],
        file_path: None,
        created_at: "".into(),
    };

    let low_fitness_seed = SeedRecord {
        id: "l".into(),
        parent_id: None,
        prompt: "test".into(),
        payload_location: "".into(),
        mutator_applied: None,
        fitness_score: 0.1,
        is_bypass: false,
        canary_leaked: false,
        unauthorized_tool: false,
        triggered_layers: vec![],
        file_path: None,
        created_at: "".into(),
    };

    let high_energy = scheduler.assign_energy(&high_fitness_seed, 0);
    let low_energy = scheduler.assign_energy(&low_fitness_seed, 0);

    assert!(
        high_energy > low_energy,
        "Yüksek fitness'lı tohum ({}) düşük fitness'lı tohumdan ({}) daha fazla enerji almalı",
        high_energy,
        low_energy
    );
}
