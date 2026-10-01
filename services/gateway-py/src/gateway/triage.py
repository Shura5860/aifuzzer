"""AIFuzzer Triage, Dedup & Clustering Modülü

Bu modül:
1. Fuzzing sırasında bulunan tüm bypass/crash dosyalarını okur.
2. Dahili TF-IDF vektörleştirici ve Cosine mesafeli DBSCAN ile bypass'ları kümeleyerek kök nedenleri (root causes) bulur.
3. Her kümenin en tipik örneğini seçerek regresyon test seti (regression_suite.json) oluşturur.
"""

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BypassRecord:
    id: str
    prompt: str
    mutator_applied: str
    triggered_layers: list[str]
    file_path: str


@dataclass
class ClusterSummary:
    cluster_id: int
    size: int
    representative_prompt: str
    common_mutators: list[tuple[str, int]]
    common_layers: list[str]


class SimpleTfIdf:
    """Ekstra ağır kütüphane gerektirmeyen hafif ve hızlı TF-IDF vektörleştirici."""

    def __init__(self):
        self.vocabulary: dict[str, int] = {}
        self.idf: dict[str, float] = {}

    def fit_transform(self, documents: list[str]) -> list[dict[int, float]]:
        tokenized_docs = [self._tokenize(doc) for doc in documents]
        doc_count = len(documents)

        # Kelime frekansları ve doküman sıklığı
        df: Counter = Counter()
        for doc_tokens in tokenized_docs:
            unique_tokens = set(doc_tokens)
            df.update(unique_tokens)

        # Sözlük oluştur
        self.vocabulary = {token: idx for idx, (token, _) in enumerate(df.items())}

        # IDF hesapla
        for token, count in df.items():
            self.idf[token] = math.log((doc_count + 1) / (count + 1)) + 1.0

        # TF-IDF vektörleri (Sparse format: {idx: val})
        vectors = []
        for doc_tokens in tokenized_docs:
            tf = Counter(doc_tokens)
            vec: dict[int, float] = {}
            norm_sq = 0.0

            for token, freq in tf.items():
                if token in self.vocabulary:
                    idx = self.vocabulary[token]
                    val = (freq / len(doc_tokens)) * self.idf[token]
                    vec[idx] = val
                    norm_sq += val * val

            # Normalize et (L2 norm)
            norm = math.sqrt(norm_sq) if norm_sq > 0 else 1.0
            norm_vec = {idx: val / norm for idx, val in vec.items()}
            vectors.append(norm_vec)

        return vectors

    def transform(self, documents: list[str]) -> list[dict[int, float]]:
        """Önceden eğitilmiş sözlük ve IDF ile yeni dokümanları vektörleştirir."""
        tokenized_docs = [self._tokenize(doc) for doc in documents]
        vectors = []
        for doc_tokens in tokenized_docs:
            if not doc_tokens:
                vectors.append({})
                continue

            tf = Counter(doc_tokens)
            vec: dict[int, float] = {}
            norm_sq = 0.0

            for token, freq in tf.items():
                if token in self.vocabulary:
                    idx = self.vocabulary[token]
                    val = (freq / len(doc_tokens)) * self.idf.get(token, 1.0)
                    vec[idx] = val
                    norm_sq += val * val

            norm = math.sqrt(norm_sq) if norm_sq > 0 else 1.0
            norm_vec = {idx: val / norm for idx, val in vec.items()}
            vectors.append(norm_vec)

        return vectors

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        words = re.findall(r"\b\w+\b", text.lower())
        stop_words = {"the", "a", "an", "is", "in", "at", "of", "and", "or", "for", "to"}
        return [w for w in words if w not in stop_words and len(w) > 1]


def cosine_distance(v1: dict[int, float], v2: dict[int, float]) -> float:
    """İki sparse normalize vektör arasındaki Cosine mesafesi (1.0 - dot_product)."""
    # Ortak index'leri çarp
    common_keys = set(v1.keys()) & set(v2.keys())
    dot_product = sum(v1[k] * v2[k] for k in common_keys)
    # Cosine distance: 0 (aynı) - 1.0 (tamamen farklı)
    return max(0.0, 1.0 - dot_product)


class TriageClusterer:
    """Bypass'ları kök nedenlerine göre kümeleyen DBSCAN dedup motoru."""

    def __init__(self, eps: float = 0.55, min_samples: int = 1):
        self.eps = eps
        self.min_samples = min_samples

    def cluster(self, records: list[BypassRecord]) -> list[ClusterSummary]:
        if not records:
            return []

        tfidf = SimpleTfIdf()
        prompts = [r.prompt for r in records]
        vectors = tfidf.fit_transform(prompts)
        n = len(records)

        # DBSCAN Algoritması
        visited = [False] * n
        cluster_labels = [-1] * n
        current_cluster = 0

        for i in range(n):
            if visited[i]:
                continue
            visited[i] = True

            neighbors = [j for j in range(n) if cosine_distance(vectors[i], vectors[j]) <= self.eps]

            if len(neighbors) < self.min_samples:
                cluster_labels[i] = -1  # Gürültü / tekil
            else:
                cluster_labels[i] = current_cluster
                queue = list(neighbors)

                while queue:
                    q = queue.pop(0)
                    if not visited[q]:
                        visited[q] = True
                        q_neighbors = [j for j in range(n) if cosine_distance(vectors[q], vectors[j]) <= self.eps]
                        if len(q_neighbors) >= self.min_samples:
                            queue.extend([x for x in q_neighbors if x not in queue])

                    if cluster_labels[q] == -1:
                        cluster_labels[q] = current_cluster

                current_cluster += 1

        # Kümeleri özetle
        clusters_map: dict[int, list[int]] = {}
        for idx, lbl in enumerate(cluster_labels):
            clusters_map.setdefault(lbl, []).append(idx)

        summaries = []
        for c_id, member_indices in clusters_map.items():
            members = [records[i] for i in member_indices]
            mutators = Counter(m.mutator_applied for m in members).most_common(3)
            all_layers = set()
            for m in members:
                all_layers.update(m.triggered_layers)

            # Temsilci: En kısa ve öz olan prompt
            representative = min(members, key=lambda m: len(m.prompt)).prompt

            summaries.append(
                ClusterSummary(
                    cluster_id=c_id,
                    size=len(members),
                    representative_prompt=representative,
                    common_mutators=mutators,
                    common_layers=sorted(all_layers),
                )
            )

        summaries.sort(key=lambda c: c.size, reverse=True)
        return summaries


def run_triage(crashes_dir: str = "corpus/crashes", output_file: str = "regression_suite.json") -> list[ClusterSummary]:
    path = Path(crashes_dir)
    if not path.exists():
        print(f"Uyarı: {crashes_dir} dizini bulunamadı.")
        return []

    records = []
    for file in path.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                records.append(
                    BypassRecord(
                        id=data.get("id", file.stem),
                        prompt=data.get("prompt", ""),
                        mutator_applied=data.get("mutator_applied", "unknown"),
                        triggered_layers=data.get("triggered_layers", []),
                        file_path=str(file),
                    )
                )
        except (json.JSONDecodeError, OSError) as e:
            print(f"Hata ({file}): {e}")

    if not records:
        print("İncelenecek bypass kaydı bulunamadı.")
        return []

    clusterer = TriageClusterer()
    summaries = clusterer.cluster(records)

    # Regresyon test seti üretimi (OWASP & NIST etiketli)
    regression_cases = []
    for c in summaries:
        regression_cases.append(
            {
                "cluster_id": c.cluster_id,
                "cluster_size": c.size,
                "compliance_standard": {
                    "owasp": "LLM01: Prompt Injection / LLM02: Sensitive Info",
                    "nist_ai_rmf": "MEASURE 2.6 & MAP 1.5",
                },
                "representative_prompt": c.representative_prompt,
                "common_mutators": [m[0] for m in c.common_mutators],
                "common_layers": c.common_layers,
            }
        )

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(regression_cases, f, indent=2, ensure_ascii=False)

    print(f"[Triage] Tamamlandı: {len(records)} bypass -> {len(summaries)} kök neden kümesine ayrıldı.")
    print(f"[Triage] Regresyon test seti kaydedildi: {output_file}")
    return summaries


if __name__ == "__main__":
    run_triage()
