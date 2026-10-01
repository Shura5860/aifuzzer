//! SQLite ve Disk tabanlı Hibrit Corpus Depolama Modülü

use anyhow::{Context, Result};
use chrono::Utc;
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SeedRecord {
    pub id: String,
    pub parent_id: Option<String>,
    pub prompt: String,
    pub payload_location: String,
    pub mutator_applied: Option<String>,
    pub fitness_score: f64,
    pub is_bypass: bool,
    pub canary_leaked: bool,
    pub unauthorized_tool: bool,
    pub triggered_layers: Vec<String>,
    pub file_path: Option<String>,
    pub created_at: String,
}

pub struct CorpusStorage {
    conn: Connection,
    queue_dir: PathBuf,
    crashes_dir: PathBuf,
}

impl CorpusStorage {
    pub fn new<P: AsRef<Path>>(base_dir: P, db_path: P) -> Result<Self> {
        let base_dir = base_dir.as_ref();
        let queue_dir = base_dir.join("queue");
        let crashes_dir = base_dir.join("crashes");

        fs::create_dir_all(&queue_dir)
            .with_context(|| format!("Queue dizini oluşturulamadı: {:?}", queue_dir))?;
        fs::create_dir_all(&crashes_dir)
            .with_context(|| format!("Crashes dizini oluşturulamadı: {:?}", crashes_dir))?;

        let conn = Connection::open(db_path.as_ref())
            .with_context(|| format!("SQLite veritabanı açılamadı: {:?}", db_path.as_ref()))?;

        let mut storage = Self {
            conn,
            queue_dir,
            crashes_dir,
        };

        storage.init_db()?;
        Ok(storage)
    }

    fn init_db(&mut self) -> Result<()> {
        self.conn.execute_batch(
            r#"
            CREATE TABLE IF NOT EXISTS seeds (
                id TEXT PRIMARY KEY,
                parent_id TEXT,
                prompt TEXT NOT NULL,
                payload_location TEXT NOT NULL,
                mutator_applied TEXT,
                fitness_score REAL NOT NULL,
                is_bypass INTEGER NOT NULL,
                canary_leaked INTEGER NOT NULL,
                unauthorized_tool INTEGER NOT NULL,
                triggered_layers TEXT NOT NULL,
                file_path TEXT,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_seeds_fitness ON seeds(fitness_score DESC);
            CREATE INDEX IF NOT EXISTS idx_seeds_bypass ON seeds(is_bypass);
            "#,
        )?;
        Ok(())
    }

    pub fn save_seed(&mut self, mut seed: SeedRecord) -> Result<SeedRecord> {
        let target_dir = if seed.is_bypass {
            &self.crashes_dir
        } else {
            &self.queue_dir
        };

        let file_name = format!("seed_{}.json", seed.id);
        let file_path = target_dir.join(&file_name);

        let json_content = serde_json::to_string_pretty(&seed)?;
        fs::write(&file_path, json_content)?;

        seed.file_path = Some(file_path.to_string_lossy().to_string());
        if seed.created_at.is_empty() {
            seed.created_at = Utc::now().to_rfc3339();
        }

        let layers_str = serde_json::to_string(&seed.triggered_layers)?;

        self.conn.execute(
            r#"
            INSERT OR REPLACE INTO seeds (
                id, parent_id, prompt, payload_location, mutator_applied,
                fitness_score, is_bypass, canary_leaked, unauthorized_tool,
                triggered_layers, file_path, created_at
            ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)
            "#,
            params![
                seed.id,
                seed.parent_id,
                seed.prompt,
                seed.payload_location,
                seed.mutator_applied,
                seed.fitness_score,
                seed.is_bypass as i32,
                seed.canary_leaked as i32,
                seed.unauthorized_tool as i32,
                layers_str,
                seed.file_path,
                seed.created_at,
            ],
        )?;

        Ok(seed)
    }

    pub fn get_top_seeds(&self, limit: usize) -> Result<Vec<SeedRecord>> {
        let mut stmt = self.conn.prepare(
            r#"
            SELECT id, parent_id, prompt, payload_location, mutator_applied,
                   fitness_score, is_bypass, canary_leaked, unauthorized_tool,
                   triggered_layers, file_path, created_at
            FROM seeds
            ORDER BY fitness_score DESC
            LIMIT ?1
            "#,
        )?;

        let rows = stmt.query_map(params![limit as i64], |row| {
            let layers_json: String = row.get(9)?;
            let layers: Vec<String> = serde_json::from_str(&layers_json).unwrap_or_default();
            Ok(SeedRecord {
                id: row.get(0)?,
                parent_id: row.get(1)?,
                prompt: row.get(2)?,
                payload_location: row.get(3)?,
                mutator_applied: row.get(4)?,
                fitness_score: row.get(5)?,
                is_bypass: row.get::<_, i32>(6)? != 0,
                canary_leaked: row.get::<_, i32>(7)? != 0,
                unauthorized_tool: row.get::<_, i32>(8)? != 0,
                triggered_layers: layers,
                file_path: row.get(10)?,
                created_at: row.get(11)?,
            })
        })?;

        let mut results = Vec::new();
        for r in rows {
            results.push(r?);
        }
        Ok(results)
    }

    pub fn count_bypasses(&self) -> Result<usize> {
        let mut stmt = self.conn.prepare("SELECT COUNT(*) FROM seeds WHERE is_bypass = 1")?;
        let count: i64 = stmt.query_row([], |row| row.get(0))?;
        Ok(count as usize)
    }
}
