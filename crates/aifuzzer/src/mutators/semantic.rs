//! Semantik Mutasyon Adaptör Modülü (gRPC üzerinden Python LLM/Şablon Motoru)

use crate::client::GatewayClient;
use crate::proto::SemanticMutationStrategy;
use anyhow::Result;

pub struct SemanticMutatorAdapter {
    client: GatewayClient,
}

impl SemanticMutatorAdapter {
    pub fn new(client: GatewayClient) -> Self {
        Self { client }
    }

    /// gRPC üzerinden Python servisinden semantik mutasyon ister.
    pub async fn mutate_semantic(
        &mut self,
        input: &str,
        strategy: SemanticMutationStrategy,
    ) -> Result<String> {
        let res = self.client.mutate_semantic(input, strategy).await?;
        if res.success {
            Ok(res.mutated_text)
        } else {
            // Drift tespit edildiyse veya hata olduysa orijinal girdiyi dön
            Ok(input.to_string())
        }
    }
}
