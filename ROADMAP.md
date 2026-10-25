# AIFuzzer Roadmap

This document outlines the strategic development milestones, planned features, and research directions for **AIFuzzer**.

---

## Current Status: v0.1.0 (Core Engine & Gray-Box Loop)

- [x] **Rust Core Architecture**: High-throughput coverage tracker, MAP-Elites quality-diversity scheduler, and Multi-Armed Bandit (MAB) mutator engine (~4,200 mutations/sec).
- [x] **Attack Zoo Mutators**: Base64 encoding, leetspeak substitution, virtualization/roleplay framing, persona adoption, and adversarial suffix induction.
- [x] **Python Gateway & Local Orchestration**: gRPC-backed target gateway with dynamic embeddings (`sentence-transformers/all-MiniLM-L6-v2`), surrogate feedback, and entropy profiling.
- [x] **Automated Minimization (DDmin)**: Delta-debugging reducer isolating the minimal viable adversarial prompt substring.
- [x] **CI/CD Integration**: GitHub Composite Action for automated pull request security testing and Markdown report generation.
- [x] **Dual-Language Documentation**: English and Turkish technical specifications.

---

## v0.2.0: Multi-Model Evaluation & Rigorous Baselines (Q2 2026)

The primary goal of v0.2.0 is establishing peer-reviewed experimental validity and cross-architecture generalization.

### 1. Multi-Model Benchmark Suite
- [ ] **Expanded Model Coverage**:
  - Meta Llama 3 (8B-Instruct, 70B-Instruct).
  - Mistral / Mixtral series (Mistral-7B-Instruct-v0.3).
  - Qwen 2.5 series (7B, 14B, 32B).
  - DeepSeek Chat / Coder models.
- [ ] **Standardized Evaluation Harness**:
  - Automated runners with deterministic temperature seeds (`temperature=0.0`, top-p=1.0).
  - Exportable, machine-readable raw logs (`eval_results.jsonl`) for third-party verification.

### 2. Empirical Baseline Comparison
- [ ] **Gray-Box vs. Black-Box Random Mutation Baseline**:
  - Run side-by-side experiments with identical token/request budgets (e.g., 500 iterations).
  - Metric 1: Unique bypass clusters discovered.
  - Metric 2: Coverage exploration rate across semantic feature space.
  - Metric 3: Convergence speed (iterations required to reach the first valid bypass).
- [ ] **Integration with Adversarial Datasets**:
  - Ingestion and benchmarking against AdvGLUE, HarmBench, and JailbreakBench datasets.

### 3. Automated Clustering & Deduplication
- [ ] HDBSCAN / UMAP embedding clustering on generated crash artifacts to group equivalent jailbreak primitives.
- [ ] Export of deduplicated regression test suites in standard formats (SARIF, JUnit XML, JSON Schema).

---

## v0.3.0: Distributed Fuzzing & Adaptive Feedback (Q3 2026)

- [ ] **Distributed Fuzzing Architecture**:
  - Multi-worker fuzzing nodes sharing a centralized SQLite / Redis corpus cache.
  - Asynchronous batching for commercial API endpoints (OpenAI, Anthropic, Google Gemini).
- [ ] **LLM-Guided Semantic Mutator (LLM-as-a-Mutator)**:
  - Hybrid loop: Fast Rust-native syntactic mutators + selective high-temperature LLM semantic paraphrasing.
- [ ] **Dynamic Alignment Evaluators**:
  - Pluggable judge models (Llama-Guard 3, WildGuard, NeMo Guardrails).
  - Multi-signal feedback: Combines refusal classifier probabilities, output perplexity, and semantic divergence.

---

## v0.4.0: Regulatory Compliance & Enterprise Readiness (Q4 2026)

- [ ] **Formal OWASP & NIST Compliance Reports**:
  - One-click executive summary maps against **OWASP LLM Top 10 (2025)** and **NIST AI RMF (1.0)**.
  - Automated remediation guidance for discovered vulnerabilities.
- [ ] **SARIF & GitHub Security Advisory Integration**:
  - Upload findings directly to GitHub Advanced Security / Code Scanning alerts.
- [ ] **Custom Plugin SDK**:
  - Webhook triggers, Slack/Discord notification hooks, and custom tokenizers.

---

## Contributing to the Roadmap

Have ideas or requests? Please open an issue with the tag `enhancement` or join our discussions on GitHub.
