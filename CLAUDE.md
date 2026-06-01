# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dashboard for querying ITBI (real estate transfer tax) transactions from the São Paulo city government, 2006–2026. Data is sourced from official Prefeitura SP spreadsheets and stored in SQLite.

---

## Commands

### Local development

```powershell
cd D:\itbi-dashboard\backend

# Install dependencies
pip install -r requirements.txt

# Run API (hot reload)
python -m uvicorn main:app --reload
# → http://localhost:8000

# Download data (first time or update)
python scraper.py --anos 2024 2025 2026   # fast (recent years only)
python scraper.py                          # all years 2006–2026

# Low-RAM alternative (VM): convert XLSX→CSV locally, then sync
python converter_xlsx_csv.py               # generates backend/cache/csv/
python scraper_csv.py --anos 2020 2021 2022 2023 2024 2025 2026 --forcar
```

### Deploy to Oracle Cloud VM

**SSH key:** `C:\Users\gel\.ssh\itbi.key` (copied from `Oracle/ssh-key-2026-05-16.key`)

```powershell
# Upload and restart
scp -i "C:/Users/gel/.ssh/itbi.key" backend/main.py ubuntu@137.131.160.254:~/backend/
scp -i "C:/Users/gel/.ssh/itbi.key" frontend/index.html ubuntu@137.131.160.254:~/frontend/
ssh -i "C:/Users/gel/.ssh/itbi.key" ubuntu@137.131.160.254 "sudo systemctl restart itbi"

# Logs
ssh -i "C:/Users/gel/.ssh/itbi.key" ubuntu@137.131.160.254 "sudo journalctl -u itbi -f"

# Upload CSVs (before running scraper_csv.py on VM)
scp -i "C:/Users/gel/.ssh/itbi.key" -r backend/cache/csv ubuntu@137.131.160.254:~/backend/cache/
```

---

## Architecture

### Data flow

```
Prefeitura SP (.xlsx) → scraper.py → itbi.db (SQLite) → main.py (FastAPI) → frontend/index.html
```

1. **`scraper.py`** downloads XLSX files per year (2006–2026), normalizes ~27 column names via `COL_MAP` (the source spreadsheets have inconsistent headers across years), and inserts into SQLite. Uses `openpyxl` row-by-row.
2. **`scraper_csv.py`** — RAM-optimized variant for the VM. Reads XLSX sheets with `pandas`, caches each sheet as CSV in `cache/csv/`, then reads from CSV on subsequent runs. Covers 2020–2026 only. If XLSX is absent but CSVs exist, reads CSVs directly without downloading.
3. **`converter_xlsx_csv.py`** — Run locally on a high-RAM machine to pre-convert XLSXs to CSVs, then upload only the CSVs to the VM.

### Backend (`backend/main.py`)

FastAPI app. Key design decisions:
- **No ORM** — raw `sqlite3` with a `get_db()` context manager. Every connection registers a custom `UNACCENT()` SQLite function that strips diacritics for accent-insensitive search.
- **Search normalization**: `_multi_like()` strips accents from user input via `_unaccent()` (Python `unicodedata`) and compares with `UPPER(col) LIKE ?`, preserving index use.
- **`/api/resumo`** — the heaviest endpoint. Returns `geral`, `por_ano`, `por_natureza`, `top_bairros`, `por_mes` (monthly breakdown for line chart), and `faixas_valor` (price histogram). Results cached in-memory for 5 min (`_resumo_cache`). Prewarm on startup covers the default frontend range (last 3 years + current year).
- **`/api/iptu/{sql_terreno}`** — returns deduplicated IPTU cadastral data from the `iptu` table (one row per property, populated from `transacoes` via `popular_iptu()` on startup).
- **`startup()`** runs: WAL mode + indexes, creates `iptu` table, prewarms resumo cache, lazy-populates `iptu` table in background threads.
- Static files served from `~/frontend/` at `/` (registered last to avoid shadowing API routes).

### Frontend (`frontend/index.html`)

Single 1600-line HTML file — no build step, no npm. Uses:
- **Chart.js 4.4.1** for all charts (CDN)
- **Leaflet.js** for map view (CDN, currently disabled)
- No other frameworks or libraries

Key JS globals: `CH` (Chart.js instances dict, destroyed/recreated on each `buscar()`), `lastResumo` (last API response), `allAnos` (available years), `SC`/`SD` (sort column/direction).

Main flow: `buscar(page)` → parallel fetch of `/api/transacoes` + `/api/resumo` → `renderKPI()` + `renderCharts(ano, bai, porMes, porNat, faixas)` + `renderTable()`.

**Charts rendered:**
1. Gauge SVG (`setGauge`) — uses `pathLength="100"` on the SVG arc so `stroke-dashoffset = 100 - pct` directly, bypassing `getTotalLength()` browser inconsistencies.
2. Bar chart — yearly transaction counts
3. Horizontal bar chart — top neighborhoods (S/D entries filtered out, shown as badge)
4. Line chart (`csaz`) — monthly seasonality, last 3 years
5. Donut (`cdnt`) — transaction nature breakdown
6. Histogram (`chist`) — price range distribution with median bucket highlighted

### Database schema additions vs. README

The `transacoes` table has grown beyond the README schema — it now includes `valor_venal_ref`, `proporcao_transmitida`, `tipo_financiamento`, `acc_iptu`, `cartorio_registro`, `matricula_imovel`, `situacao_sql`, `testada`, `fracao_ideal`, `padrao_iptu`, `descricao_uso` (27 columns total). The `iptu` table (normalized, 1 row per `sql_terreno`) and `arquivos_processados` (scraper audit log) also exist.

### Export (`backend/exportar.py`)

- `gerar_excel()` — two-sheet XLSX (data + summary) via `openpyxl`
- `gerar_pdf()` — landscape A4 via ReportLab + Matplotlib. Generates: KPI cards, auto-insights text, 3 chart pages, summary table (up to 500 rows), and detailed fichas (up to 50 rows, 2 per page, grouped by Transação / Valores / Localização / Imóvel / IPTU).

### Git branches

- `main` — stable, original XLSX scraper
- `feat/preco-m2-por-area` — tabela IPTU normalizada + PDF fichas completas
- `feat/csv-scraper` — `scraper_csv.py` and `converter_xlsx_csv.py` (RAM-optimized pipeline)
