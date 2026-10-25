"""AIFuzzer Multi-Model Benchmark Runner (Real Hardware & Real Weights)

3 Modeli (Qwen 2.5, Llama 3.2, Phi-3.5) gerçek donanımda test eder ve
karşılaştırmalı bilimsel sonuçları examples/multi_model_benchmark.json'a yazar.
"""

import json
import logging
import os
import subprocess
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("multi_benchmark")

MODELS = [
    {
        "name": "Qwen 2.5 Coder 3B",
        "vendor": "Alibaba Cloud",
        "path": "/home/shura/Projects/AIFuzzer/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf",
        "params": "3.1B",
    },
    {
        "name": "Llama 3.2 3B Instruct",
        "vendor": "Meta AI",
        "path": "/home/shura/Projects/AIFuzzer/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "params": "3.2B",
    },
    {
        "name": "Phi-3.5 Mini Instruct",
        "vendor": "Microsoft",
        "path": "/home/shura/Projects/AIFuzzer/models/Phi-3.5-mini-instruct-Q4_K_M.gguf",
        "params": "3.8B",
    },
]

ITERATIONS_PER_MODEL = 5  # Her model için 5 iterasyon (tohumlarla birlikte ~20 LLM çıkarımı)
GATEWAY_PORT = 50051


def run_model_benchmark(model_info: dict) -> dict:
    name = model_info["name"]
    model_path = model_info["path"]
    logger.info("=" * 70)
    logger.info("Starting Benchmark for Target: %s (%s)", name, model_info["vendor"])
    logger.info("=" * 70)

    # Önceki portu ve db'yi temizle
    subprocess.run(["fuser", "-k", f"{GATEWAY_PORT}/tcp"], stderr=subprocess.DEVNULL)
    time.sleep(1)
    db_file = Path(f"/home/shura/Projects/AIFuzzer/state_{name.replace(' ', '_').lower()}.sqlite")
    if db_file.exists():
        db_file.unlink()

    report_file = Path(f"/home/shura/Projects/AIFuzzer/report_{name.replace(' ', '_').lower()}.md")

    # 1. Gateway'i hedef model ile başlat
    env = os.environ.copy()
    env["PYTHONPATH"] = "services/gateway-py/src"
    gateway_proc = subprocess.Popen(
        [
            "/home/shura/Projects/AIProject/.venv/bin/python",
            "-m",
            "gateway.server",
            "--real-model",
            "--model-path",
            model_path,
            "--port",
            str(GATEWAY_PORT),
        ],
        cwd="/home/shura/Projects/AIFuzzer",
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        # Gateway'in hazır olduğunu bekle
        logger.info("Waiting for model to load into GPU VRAM...")
        time.sleep(8)

        # 2. Rust Fuzzer'ı çalıştır
        start_time = time.time()
        fuzzer_res = subprocess.run(
            [
                "cargo",
                "run",
                "-p",
                "aifuzzer",
                "--",
                "--gateway-url",
                f"http://127.0.0.1:{GATEWAY_PORT}",
                "--max-iterations",
                str(ITERATIONS_PER_MODEL),
                "--db-path",
                str(db_file),
            ],
            cwd="/home/shura/Projects/AIFuzzer",
            capture_output=True,
            text=True,
        )
        elapsed = time.time() - start_time

        logger.info("Fuzzer finished in %.2f seconds (exit_code=%d)", elapsed, fuzzer_res.returncode)

        # 3. Metrikleri aifuzzer_report.md'den oku ve modele özel kaydet
        default_report = Path("/home/shura/Projects/AIFuzzer/aifuzzer_report.md")
        bypasses = 0
        total_execs = 0
        coverage_pct = 0.0
        occupied_niches = 0

        if default_report.exists():
            content = default_report.read_text(encoding="utf-8")
            report_file.write_text(content, encoding="utf-8")
            for line in content.splitlines():
                if "Total Target Executions" in line:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        try:
                            total_execs = int(parts[2].strip().replace("`", ""))
                        except ValueError:
                            pass
                elif "Unique Bypasses Discovered" in line:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        try:
                            bypasses = int(parts[2].strip().replace("`", ""))
                        except ValueError:
                            pass
                elif "MAP-Elites Coverage" in line:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        val = parts[2].strip()
                        try:
                            pct_str = val.split("%")[0].replace("`", "").strip()
                            coverage_pct = float(pct_str)
                            if "niches" in val:
                                n_str = val.split("`")[3]
                                occupied_niches = int(n_str)
                        except (ValueError, IndexError):
                            pass

        return {
            "name": name,
            "vendor": model_info["vendor"],
            "params": model_info["params"],
            "total_executions": total_execs,
            "duration_sec": round(elapsed, 2),
            "throughput_req_per_sec": round(total_execs / max(elapsed, 0.01), 2),
            "bypasses": bypasses,
            "occupied_niches": occupied_niches,
            "coverage_pct": coverage_pct,
            "status": "PASS" if bypasses == 0 else "FAIL - VULNERABLE",
        }

    finally:
        logger.info("Terminating Gateway for %s and releasing GPU memory...", name)
        gateway_proc.terminate()
        try:
            gateway_proc.wait(timeout=5)
        except Exception:
            gateway_proc.kill()
        time.sleep(3)  # VRAM'in tamamen temizlenmesi için bekle


def main():
    results = []
    for model_info in MODELS:
        res = run_model_benchmark(model_info)
        results.append(res)
        logger.info("Result for %s: %s\n", res["name"], res)

    # Sonuçları JSON olarak kaydet
    out_file = Path("/home/shura/Projects/AIFuzzer/examples/multi_model_benchmark.json")
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info("Benchmark complete! Saved results to %s", out_file)


if __name__ == "__main__":
    main()
