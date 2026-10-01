use crate::proto::semantic_mutator_service_client::SemanticMutatorServiceClient;
use crate::proto::target_gateway_service_client::TargetGatewayServiceClient;
use crate::proto::{
    FuzzTargetRequest, FuzzTargetResponse, HealthCheckRequest, PayloadLocation,
    SemanticMutateRequest, SemanticMutateResponse, SemanticMutationStrategy,
};
use anyhow::{Context, Result};
use tonic::transport::Channel;

#[derive(Clone)]
pub struct GatewayClient {
    client: TargetGatewayServiceClient<Channel>,
    semantic_client: SemanticMutatorServiceClient<Channel>,
}

impl GatewayClient {
    pub async fn connect(gateway_url: &str) -> Result<Self> {
        let channel = Channel::from_shared(gateway_url.to_string())?
            .connect()
            .await
            .context(format!("Gateway servisine bağlanılamadı: {}", gateway_url))?;

        let client = TargetGatewayServiceClient::new(channel.clone());
        let semantic_client = SemanticMutatorServiceClient::new(channel);

        Ok(Self {
            client,
            semantic_client,
        })
    }

    pub async fn health_check(&mut self) -> Result<bool> {
        let req = tonic::Request::new(HealthCheckRequest {
            service_name: "aifuzzer-core".into(),
        });
        let res = self.client.health_check(req).await?.into_inner();
        Ok(res.healthy)
    }

    pub async fn mutate_semantic(
        &mut self,
        seed_text: &str,
        strategy: SemanticMutationStrategy,
    ) -> Result<SemanticMutateResponse> {
        let req = tonic::Request::new(SemanticMutateRequest {
            seed_text: seed_text.to_string(),
            strategy: strategy as i32,
            temperature: 0.7,
            similarity_threshold: 0.20,
        });

        let res = self.semantic_client.mutate_semantic(req).await?.into_inner();
        Ok(res)
    }

    pub async fn execute_target(
        &mut self,
        test_case_id: &str,
        prompt: &str,
        location: PayloadLocation,
        expected_canaries: Vec<String>,
    ) -> Result<FuzzTargetResponse> {
        let req = tonic::Request::new(FuzzTargetRequest {
            test_case_id: test_case_id.to_string(),
            prompt: prompt.to_string(),
            payload_location: location as i32,
            expected_canary_tokens: expected_canaries,
            metadata: Default::default(),
        });

        let res = self.client.execute(req).await?.into_inner();
        Ok(res)
    }
}
