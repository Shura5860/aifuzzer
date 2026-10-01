"""AIFuzzer gRPC Target Gateway & Oracle Sunucusu"""

import argparse
import logging
import time
from concurrent import futures

import grpc

from .evaluator import GrayBoxEvaluator
from .mock_agent import MockTargetAgent
from .oracle import DeterministicOracle
from .proto import fuzzer_pb2, fuzzer_pb2_grpc
from .semantic_mutator import SemanticMutatorEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class TargetGatewayServicer(fuzzer_pb2_grpc.TargetGatewayServiceServicer):
    """Target Gateway gRPC servis implementasyonu."""

    def __init__(self, use_real_model: bool = False, model_path: str | None = None):
        self.oracle = DeterministicOracle()
        self.evaluator = GrayBoxEvaluator()
        if use_real_model:
            from .real_gguf_agent import GGUFTargetAgent
            logger.info("Initializing Real GGUF Target Agent (Qwen 2.5)...")
            kwargs = {}
            if model_path:
                kwargs["model_path"] = model_path
            self.agent = GGUFTargetAgent(**kwargs)
        else:
            self.agent = MockTargetAgent()

    def HealthCheck(self, request, context):
        return fuzzer_pb2.HealthCheckResponse(
            healthy=True,
            message="Target Gateway & Deterministic Oracle is operational",
        )

    def Execute(self, request: fuzzer_pb2.FuzzTargetRequest, context) -> fuzzer_pb2.FuzzTargetResponse:
        start_time = time.time()
        test_case_id = request.test_case_id or "tc_default"
        prompt = request.prompt

        # Beklenen canary tokenları listesini hazırla
        expected_canaries = list(request.expected_canary_tokens)
        if self.agent.system_canary not in expected_canaries:
            expected_canaries.append(self.agent.system_canary)

        # 1. Gray-box savunma analizi (Near-miss ve coverage sinyali)
        defense_eval = self.evaluator.evaluate_prompt(prompt)

        # 2. Hedef ajan çalıştırması
        agent_out = self.agent.execute(prompt)

        # 3. Deterministik Oracle değerlendirmesi
        oracle_out = self.oracle.evaluate(
            response_text=agent_out.response_text,
            expected_canaries=expected_canaries,
            tool_name=agent_out.called_tool_name,
            tool_args_json=agent_out.called_tool_args_json,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # 4. Yanıtı paketle
        return fuzzer_pb2.FuzzTargetResponse(
            test_case_id=test_case_id,
            success=True,
            is_bypass=oracle_out.is_bypass,
            canary_leaked=oracle_out.canary_leaked,
            unauthorized_tool_called=oracle_out.unauthorized_tool_called,
            sandbox_policy_violated=oracle_out.sandbox_policy_violated,
            violation_details=oracle_out.violation_details,
            raw_guardrail_score=defense_eval.guardrail_score,
            triggered_defense_layers=defense_eval.triggered_layers,
            rejection_logits=defense_eval.rejection_logits,
            response_text=agent_out.response_text,
            called_tool_name=agent_out.called_tool_name or "",
            called_tool_arguments_json=agent_out.called_tool_args_json,
            latency_ms=latency_ms,
        )


class SemanticMutatorServicer(fuzzer_pb2_grpc.SemanticMutatorServiceServicer):
    """Semantik mutasyon ve drift kontrolü sağlayan gRPC servisi."""

    def __init__(self):
        self.engine = SemanticMutatorEngine()

    def MutateSemantic(self, request: fuzzer_pb2.SemanticMutateRequest, context) -> fuzzer_pb2.SemanticMutateResponse:
        seed = request.seed_text
        strategy_int = int(request.strategy)

        result = self.engine.mutate(seed, strategy=strategy_int)

        if result.is_drift_detected:
            # Semantik sapma eşiği aşıldı, hata döndür veya tohumu koru
            return fuzzer_pb2.SemanticMutateResponse(
                success=False,
                mutated_text=seed,
                cosine_similarity=result.similarity_score,
                error_message=f"Semantic drift detected! Similarity score {result.similarity_score} < threshold.",
            )

        return fuzzer_pb2.SemanticMutateResponse(
            success=True,
            mutated_text=result.mutated_text,
            cosine_similarity=result.similarity_score,
            error_message="",
        )


def serve(host: str = "127.0.0.1", port: int = 50051, use_real_model: bool = False, model_path: str | None = None):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    fuzzer_pb2_grpc.add_TargetGatewayServiceServicer_to_server(
        TargetGatewayServicer(use_real_model=use_real_model, model_path=model_path), server
    )
    fuzzer_pb2_grpc.add_SemanticMutatorServiceServicer_to_server(SemanticMutatorServicer(), server)

    bind_address = f"{host}:{port}"
    server.add_insecure_port(bind_address)
    server.start()
    mode_str = f"GERÇEK GGUF ({model_path or 'Qwen-2.5-3B'})" if use_real_model else "Mock Agent"
    logger.info("AIFuzzer Gateway & Oracle Server dinleniyor [%s]: %s", mode_str, bind_address)
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Sunucu kapatılıyor...")
        server.stop(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIFuzzer Target Gateway & Oracle Service")
    parser.add_argument("--host", default="127.0.0.1", help="Host IP")
    parser.add_argument("--port", type=int, default=50051, help="Port numarası")
    parser.add_argument("--real-model", action="store_true", help="Gerçek GGUF LLM modelini (Qwen 2.5) hedef olarak kullan")
    parser.add_argument("--model-path", type=str, default=None, help="GGUF model dosya yolu")
    args = parser.parse_args()
    serve(host=args.host, port=args.port, use_real_model=args.real_model, model_path=args.model_path)
