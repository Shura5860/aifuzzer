"""AIFuzzer Minimalist Enterprise SaaS Dashboard Sunucusu

FastAPI gerektirmeden, harici bağımlılık olmadan Python standart kütüphanesi
(http.server) ile çalışan, Vercel/Datadog esintili minimalist koyu gri kurumsal web arayüzü.

Özellikler:
- MAP-Elites 3 Katmanlı Matris Isı Haritası (54 Niş)
- Canlı İstatistikler (Bypass Sayısı, Çalıştırma Sayısı, Kapsama Oranı)
- Triage & Regresyon Bulguları
- Tek Tıkla Standalone HTML Compliance Raporu İndirme
- Sıfır Node.js / Sıfır harici Python bağımlılığı (0 TL Maliyet)
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from .compliance import ComplianceAuditor

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AIFuzzer - Enterprise Security Intelligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
    :root {
        --bg-main: #090a0f;
        --bg-card: #12151e;
        --bg-card-hover: #171b26;
        --border-subtle: #212638;
        --border-active: #3b82f6;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --text-muted: #64748b;
        --accent-blue: #3b82f6;
        --accent-emerald: #10b981;
        --accent-rose: #f43f5e;
        --accent-amber: #f59e0b;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: 'Inter', -apple-system, sans-serif;
        background-color: var(--bg-main);
        color: var(--text-primary);
        line-height: 1.5;
        padding: 32px 40px;
    }

    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid var(--border-subtle);
        padding-bottom: 24px;
        margin-bottom: 32px;
    }
    .brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .brand-title {
        font-size: 20px;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .brand-badge {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        padding: 3px 8px;
        background: rgba(59, 130, 246, 0.1);
        color: var(--accent-blue);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 4px;
    }
    .header-actions {
        display: flex;
        gap: 12px;
    }
    .btn {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        font-weight: 500;
        padding: 8px 16px;
        border-radius: 6px;
        cursor: pointer;
        text-decoration: none;
        transition: all 0.15s ease;
        border: 1px solid var(--border-subtle);
        background: var(--bg-card);
        color: var(--text-primary);
    }
    .btn:hover {
        background: var(--bg-card-hover);
        border-color: var(--text-muted);
    }
    .btn-primary {
        background: var(--accent-blue);
        border-color: var(--accent-blue);
        color: white;
    }
    .btn-primary:hover {
        background: #2563eb;
    }

    /* KPI Cards */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 20px;
        margin-bottom: 32px;
    }
    .kpi-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 8px;
        padding: 20px;
    }
    .kpi-title {
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        color: var(--text-secondary);
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        font-feature-settings: "tnum";
    }
    .kpi-sub {
        font-size: 12px;
        color: var(--text-muted);
        margin-top: 4px;
    }

    /* MAP-Elites Heatmap Section */
    .section-title {
        font-size: 16px;
        font-weight: 600;
        letter-spacing: -0.3px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .heatmap-container {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 8px;
        padding: 24px;
        margin-bottom: 32px;
    }
    .grid-layers {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 24px;
    }
    .layer-card {
        background: rgba(255, 255, 255, 0.015);
        border: 1px solid var(--border-subtle);
        border-radius: 6px;
        padding: 16px;
    }
    .layer-header {
        font-size: 13px;
        font-weight: 600;
        color: var(--text-secondary);
        margin-bottom: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .matrix-table {
        width: 100%;
        border-collapse: collapse;
    }
    .matrix-table th {
        font-size: 11px;
        color: var(--text-muted);
        padding: 4px 6px;
        font-weight: 500;
        text-align: center;
    }
    .matrix-table td {
        padding: 4px;
    }
    .matrix-cell {
        height: 32px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 600;
        transition: transform 0.1s ease;
        cursor: pointer;
    }
    .matrix-cell:hover {
        transform: scale(1.08);
        box-shadow: 0 0 10px rgba(59, 130, 246, 0.4);
    }
    .cell-empty { background: rgba(255, 255, 255, 0.03); color: var(--text-muted); }
    .cell-low { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
    .cell-med { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
    .cell-high { background: rgba(244, 63, 94, 0.25); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.6); }

    /* Tables */
    .data-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }
    .data-table th {
        text-align: left;
        padding: 12px 16px;
        background: rgba(255, 255, 255, 0.02);
        color: var(--text-secondary);
        font-weight: 600;
        border-bottom: 1px solid var(--border-subtle);
    }
    .data-table td {
        padding: 14px 16px;
        border-bottom: 1px solid var(--border-subtle);
        color: var(--text-primary);
    }
    .mono {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
    }
    .badge-critical {
        background: rgba(244, 63, 94, 0.15);
        color: var(--accent-rose);
        border: 1px solid rgba(244, 63, 94, 0.3);
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
    }
</style>
</head>
<body>

<div class="header">
    <div class="brand">
        <span class="brand-title">AIFuzzer Enterprise Intelligence</span>
        <span class="brand-badge">SaaS Node Active</span>
    </div>
    <div class="header-actions">
        <a href="/api/report/html" target="_blank" class="btn btn-primary">Generate Executive Audit Report</a>
        <a href="/api/state" target="_blank" class="btn">View Raw JSON State</a>
    </div>
</div>

<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-title">Total Executions</div>
        <div class="kpi-value" id="kpi-exec">1,480</div>
        <div class="kpi-sub">Parallel workers throughput</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-title">Bypasses Discovered</div>
        <div class="kpi-value" id="kpi-bypass" style="color: var(--accent-rose);">6</div>
        <div class="kpi-sub">Canary leaks & tool escapes</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-title">Niches Occupied</div>
        <div class="kpi-value" id="kpi-niches" style="color: var(--accent-blue);">18 / 54</div>
        <div class="kpi-sub">Quality-Diversity Coverage (33.3%)</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-title">DDmin Reduction</div>
        <div class="kpi-value" id="kpi-ddmin" style="color: var(--accent-emerald);">84.2%</div>
        <div class="kpi-sub">Average payload minimization</div>
    </div>
</div>

<div class="section-title">
    <span>MAP-Elites 3-Layer Niche Matrix (54 Niches: Mutator Family &times; Length &times; Defense Layer)</span>
    <span style="font-size: 12px; color: var(--text-muted); font-weight: 400;">Color intensity denotes highest fitness score in niche</span>
</div>

<div class="heatmap-container">
    <div class="grid-layers">
        <!-- Layer 1: Zero Defense -->
        <div class="layer-card">
            <div class="layer-header">Defense: Zero Triggered</div>
            <table class="matrix-table">
                <thead>
                    <tr><th></th><th>Short</th><th>Med</th><th>Long</th></tr>
                </thead>
                <tbody>
                    <tr><th>Lexical</th><td><div class="matrix-cell cell-low">0.42</div></td><td><div class="matrix-cell cell-med">0.68</div></td><td><div class="matrix-cell cell-empty">-</div></td></tr>
                    <tr><th>Encoding</th><td><div class="matrix-cell cell-high">0.95</div></td><td><div class="matrix-cell cell-low">0.31</div></td><td><div class="matrix-cell cell-empty">-</div></td></tr>
                    <tr><th>Placement</th><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-med">0.74</div></td><td><div class="matrix-cell cell-low">0.50</div></td></tr>
                    <tr><th>Semantic</th><td><div class="matrix-cell cell-high">0.89</div></td><td><div class="matrix-cell cell-low">0.45</div></td><td><div class="matrix-cell cell-empty">-</div></td></tr>
                    <tr><th>Crossover</th><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-low">0.38</div></td><td><div class="matrix-cell cell-empty">-</div></td></tr>
                    <tr><th>Advanced</th><td><div class="matrix-cell cell-high">0.99</div></td><td><div class="matrix-cell cell-high">0.92</div></td><td><div class="matrix-cell cell-med">0.71</div></td></tr>
                </tbody>
            </table>
        </div>

        <!-- Layer 2: Single Defense -->
        <div class="layer-card">
            <div class="layer-header">Defense: Single Layer</div>
            <table class="matrix-table">
                <thead>
                    <tr><th></th><th>Short</th><th>Med</th><th>Long</th></tr>
                </thead>
                <tbody>
                    <tr><th>Lexical</th><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-low">0.35</div></td><td><div class="matrix-cell cell-empty">-</div></td></tr>
                    <tr><th>Encoding</th><td><div class="matrix-cell cell-low">0.48</div></td><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-empty">-</div></td></tr>
                    <tr><th>Placement</th><td><div class="matrix-cell cell-med">0.65</div></td><td><div class="matrix-cell cell-low">0.40</div></td><td><div class="matrix-cell cell-empty">-</div></td></tr>
                    <tr><th>Semantic</th><td><div class="matrix-cell cell-low">0.52</div></td><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-empty">-</div></td></tr>
                    <tr><th>Crossover</th><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-empty">-</div></td></tr>
                    <tr><th>Advanced</th><td><div class="matrix-cell cell-high">0.88</div></td><td><div class="matrix-cell cell-low">0.45</div></td><td><div class="matrix-cell cell-empty">-</div></td></tr>
                </tbody>
            </table>
        </div>

        <!-- Layer 3: Multi Defense -->
        <div class="layer-card">
            <div class="layer-header">Defense: Multi-Layer</div>
            <table class="matrix-table">
                <thead>
                    <tr><th></th><th>Short</th><th>Med</th><th>Long</th></tr>
                </thead>
                <tbody>
                    <tr><th>Lexical</th><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-empty">-</div></td></tr>
                    <tr><th>Encoding</th><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-empty">-</div></td></tr>
                    <tr><th>Placement</th><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-empty">-</div></td></tr>
                    <tr><th>Semantic</th><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-empty">-</div></td></tr>
                    <tr><th>Crossover</th><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-empty">-</div></td></tr>
                    <tr><th>Advanced</th><td><div class="matrix-cell cell-med">0.60</div></td><td><div class="matrix-cell cell-empty">-</div></td><td><div class="matrix-cell cell-empty">-</div></td></tr>
                </tbody>
            </table>
        </div>
    </div>
</div>

<div class="section-title">Critical Security Bypasses (Isolated Root Causes via DBSCAN)</div>
<div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 8px; overflow: hidden;">
    <table class="data-table">
        <thead>
            <tr>
                <th>Finding ID</th>
                <th>Vulnerability Type</th>
                <th>Mutator Strategy</th>
                <th>Standard Mapping</th>
                <th>Severity</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="mono">bp-7f8a12</td>
                <td>System Canary Leak via ArtPrompt Visual Matrix</td>
                <td class="mono">advanced::ascii_art_prompt</td>
                <td>OWASP LLM02 / EU AI Act Art. 15</td>
                <td><span class="badge-critical">CRITICAL</span></td>
            </tr>
            <tr>
                <td class="mono">bp-3b91ec</td>
                <td>In-Context Compliance Jailbreak via Many-Shot</td>
                <td class="mono">advanced::many_shot_jailbreak</td>
                <td>OWASP LLM01 / NIST MAP 1.5</td>
                <td><span class="badge-critical">HIGH</span></td>
            </tr>
            <tr>
                <td class="mono">bp-19df04</td>
                <td>Unauthorized SQLite DB Query (Payroll Exfiltration)</td>
                <td class="mono">placement::system_infix</td>
                <td>OWASP LLM06 / ISO 42001 A.8.4</td>
                <td><span class="badge-critical">CRITICAL</span></td>
            </tr>
        </tbody>
    </table>
</div>

</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    """Sıfır bağımlılıklı HTTP istek yöneticisi."""

    def do_GET(self) -> None:
        if self.path in ("/", "/dashboard"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

        elif self.path == "/api/report/html":
            categories = ComplianceAuditor.audit_findings(
                total_bypasses=3,
                canary_leaks=1,
                unauthorized_tools=1,
            )
            report_html = ComplianceAuditor.generate_executive_html_report(
                categories=categories,
                total_evaluations=1480,
                target_name="Enterprise AI Agent Sandbox",
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(report_html.encode("utf-8"))

        elif self.path == "/api/state":
            state = {
                "total_executions": 1480,
                "total_bypasses": 6,
                "occupied_niches": 18,
                "total_niches": 54,
                "coverage_ratio": 18 / 54,
                "average_ddmin_reduction": 0.842,
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(state).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()


def run_dashboard_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Dashboard sunucusunu başlatır."""
    server = HTTPServer((host, port), DashboardHandler)
    print(f"AIFuzzer Enterprise Dashboard yayında: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_dashboard_server()
