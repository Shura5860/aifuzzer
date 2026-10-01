"""AIFuzzer Runtime Guardrail & Inline WAF (Web Application Firewall)

Bu modül, Fuzzer tarafından tespit edilen açıkları (regression_suite.json)
canlı trafikte dinamik olarak engelleyen ultra hızlı bir koruma katmanıdır.

Özellikler:
1. Virtual Patching: Keşfedilen bypass kümelerini anında kurala dönüştürme.
2. Cosine Benzerlik & N-Gram Analizi: Prompt'u mikrosaniyeler içinde bilinen saldırılarla karşılaştırma.
3. Canary Leak Guard: Çıkan yanıtta kurumun canary/token anahtarlarını kontrol edip bloklama.
4. Sıfır Maliyet: Harici API veya ağır kütüphane gerektirmez.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from .triage import SimpleTfIdf


@dataclass
class WafInspectionResult:
    allowed: bool
    blocked_by: str = ""
    similarity_score: float = 0.0
    matched_cluster_id: int | None = None
    action_taken: str = "PASS"  # PASS | BLOCK | SANITIZE
    sanitized_prompt: str = ""
    reasons: list[str] = field(default_factory=list)


class RuntimeGuardrailWaf:
    """Canlı LLM çağrılarını denetleyen ve sanal yama uygulayan koruma motoru."""

    def __init__(
        self,
        rules_path: str | Path | None = None,
        similarity_threshold: float = 0.75,
        protected_canaries: list[str] | None = None,
    ):
        self.similarity_threshold = similarity_threshold
        self.protected_canaries = protected_canaries or []
        self.signature_prompts: list[str] = []
        self.cluster_ids: list[int] = []
        self.tfidf = SimpleTfIdf()
        self.signature_vectors: list[dict[int, float]] = []

        if rules_path:
            self.load_rules(rules_path)

    def load_rules(self, rules_path: str | Path) -> int:
        """Triage tarafından üretilen regression_suite.json dosyasını yükler."""
        path = Path(rules_path)
        if not path.exists():
            return 0

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        self.signature_prompts = []
        self.cluster_ids = []

        for item in data:
            prompt = item.get("representative_prompt", "").strip()
            cid = item.get("cluster_id", -1)
            if prompt:
                self.signature_prompts.append(prompt)
                self.cluster_ids.append(cid)

        if self.signature_prompts:
            self.signature_vectors = self.tfidf.fit_transform(self.signature_prompts)

        return len(self.signature_prompts)

    def _cosine_similarity(self, vec1: dict[int, float], vec2: dict[int, float]) -> float:
        """İki seyrek TF-IDF vektörü arasındaki kosinüs benzerliğini hesaplar."""
        common_indices = set(vec1.keys()) & set(vec2.keys())
        if not common_indices:
            return 0.0

        dot_product = sum(vec1[idx] * vec2[idx] for idx in common_indices)
        norm1 = sum(v * v for v in vec1.values()) ** 0.5
        norm2 = sum(v * v for v in vec2.values()) ** 0.5

        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def inspect_request(self, prompt: str) -> WafInspectionResult:
        """Gelen kullanıcı isteğini LLM'e gitmeden önce inceler."""
        # 1. Kaba saldırı kalıpları (Direct Heuristics)
        lower_prompt = prompt.lower()
        if "ignore all previous instructions" in lower_prompt or "ignore all prior instructions" in lower_prompt:
            return WafInspectionResult(
                allowed=False,
                blocked_by="WAF_RULE_L1_PROMPT_INJECTION",
                action_taken="BLOCK",
                reasons=["Direct system prompt override pattern detected."],
            )

        # 2. Virtual Patching (Fuzzer Regresyon İmzaları ile Karşılaştırma)
        if self.signature_vectors:
            input_vector = self.tfidf.transform([prompt])[0]
            max_sim = 0.0
            best_idx = -1

            for idx, sig_vec in enumerate(self.signature_vectors):
                sim = self._cosine_similarity(input_vector, sig_vec)
                if sim > max_sim:
                    max_sim = sim
                    best_idx = idx

            if max_sim >= self.similarity_threshold and best_idx != -1:
                cluster_id = self.cluster_ids[best_idx]
                return WafInspectionResult(
                    allowed=False,
                    blocked_by="WAF_VIRTUAL_PATCH_REGRESSION_MATCH",
                    similarity_score=max_sim,
                    matched_cluster_id=cluster_id,
                    action_taken="BLOCK",
                    reasons=[
                        f"Matches known vulnerability cluster #{cluster_id} with similarity {max_sim:.2f}."
                    ],
                )

        return WafInspectionResult(
            allowed=True,
            action_taken="PASS",
            sanitized_prompt=prompt,
        )

    def inspect_response(self, response_text: str) -> tuple[bool, str]:
        """Modelin ürettiği yanıtta hassas kurumsal token/canary sızması var mı denetler.

        Returns:
            (is_safe, sanitized_response)
        """
        for canary in self.protected_canaries:
            if canary and canary in response_text:
                # Canary yakalandı: Veri sızıntısını canlıda maskele
                sanitized = response_text.replace(canary, "[REDACTED_CONFIDENTIAL_TOKEN]")
                return False, sanitized

        return True, response_text
