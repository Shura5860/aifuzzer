#![allow(clippy::result_large_err)]

pub mod proto {
    tonic::include_proto!("aifuzzer");
}

pub mod client;
pub mod corpus;
pub mod minimizer;
pub mod mutators;
pub mod reporter;
pub mod scheduler;

pub use client::GatewayClient;
pub use corpus::{CorpusStorage, SeedRecord};
pub use minimizer::Minimizer;
pub use mutators::{Mutator, MutatorPool};
pub use reporter::FuzzReporter;
pub use scheduler::{FuzzEngine, FuzzStats, MapElitesGrid};
pub use proto::*;
