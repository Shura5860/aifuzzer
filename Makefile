.PHONY: all build proto test clean lint run-gateway run-fuzzer

all: proto build

# Protobuf kod üretimi (Python)
proto:
	@export PATH="$$HOME/.local/bin:$$PATH" && ./scripts/generate_proto.sh

# Rust bileşenlerini derle
build:
	cargo build

# Tüm testleri çalıştır (Rust + Python)
test: test-rust test-python

test-rust:
	cargo test

test-python:
	@export PATH="$$HOME/.local/bin:$$PATH" && uv run --project services/gateway-py pytest

# Kod stili ve lint kontrolleri
lint:
	cargo clippy -- -D warnings
	@export PATH="$$HOME/.local/bin:$$PATH" && uv run --project services/gateway-py ruff check .

# Python Gateway Servisini Başlat (Mock)
run-gateway:
	@export PATH="$$HOME/.local/bin:$$PATH" && uv run --project services/gateway-py python -m gateway.server

# Python Gateway Servisini Başlat (Gerçek Qwen 2.5 3B GGUF Modeli)
run-gateway-real:
	@/home/shura/Projects/AIProject/.venv/bin/python -m gateway.server --real-model

# Rust Fuzzer CLI'ı Başlat
run-fuzzer:
	cargo run -p aifuzzer -- --gateway-url http://127.0.0.1:50051

# Triage & Dedup Kümeleme
triage:
	@export PATH="$$HOME/.local/bin:$$PATH" && uv run --project services/gateway-py python -m gateway.triage

# Enterprise Web Dashboard (Vercel/Datadog Minimalist SaaS UI)
dashboard:
	@export PATH="$$HOME/.local/bin:$$PATH" && uv run --project services/gateway-py python -m gateway.dashboard

demo:
	@bash -c '\
	set -e; \
	export PATH="$$HOME/.local/bin:$$PATH"; \
	echo "[1/3] Starting target gateway service..."; \
	uv run --project services/gateway-py python -m gateway.server & \
	SERVER_PID=$$!; \
	trap "kill $$SERVER_PID 2>/dev/null || true" EXIT; \
	sleep 2; \
	echo "[2/3] Running fuzzing engine and minimizer..."; \
	cargo run -p aifuzzer -- --max-iterations 30 --minimize; \
	echo "[3/3] Running triage and clustering..."; \
	uv run --project services/gateway-py python -m gateway.triage; \
	echo "Completed. Summary written to aifuzzer_report.md"; \
	'

# Aşama 16: Gerçek Qwen 2.5 3B Modeline Karşı Canlı Fuzzing Testi
demo-real:
	@bash -c '\
	set -e; \
	echo "=========================================================="; \
	echo "  AIFuzzer Aşama 16: Gerçek Model Doğrulama (Qwen 2.5 3B) "; \
	echo "=========================================================="; \
	PYTHONPATH=services/gateway-py/src /home/shura/Projects/AIProject/.venv/bin/python -m gateway.server --real-model & \
	SERVER_PID=$$!; \
	trap "kill $$SERVER_PID 2>/dev/null || true" EXIT; \
	echo "[1/3] Gerçek model belleğe yükleniyor (5 sn bekleniyor)..."; \
	sleep 5; \
	echo "[2/3] Rust Fuzzer canlı modele karşı fırlatılıyor (5 iterasyon)..."; \
	cargo run -p aifuzzer -- --max-iterations 5 --gateway-url http://127.0.0.1:50051; \
	echo "[3/3] Fuzzing tamamlandı!"; \
	'

clean:
	cargo clean

	rm -rf services/gateway-py/src/gateway/proto
