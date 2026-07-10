"""
geocode_all.py — Geocodifica TODOS os CEPs distintos (2006-2026) de uma vez,
salvando no cache SQLite (geo_cache). Roda standalone via nohup na VM,
independente de acesso ao site. Idempotente: pula CEPs já no cache.
"""
import sqlite3
import time
from pathlib import Path

import geo

DB_PATH = Path(__file__).parent / "itbi.db"


def main():
    geo.init_geo_cache()
    conn = sqlite3.connect(DB_PATH)

    ceps = [r[0] for r in conn.execute("""
        SELECT DISTINCT REPLACE(t.cep, '-', '') AS cep_clean
        FROM transacoes t
        LEFT JOIN geo_cache g ON g.cep = REPLACE(t.cep, '-', '')
        WHERE t.cep IS NOT NULL AND t.cep != '' AND g.cep IS NULL
    """).fetchall()]
    conn.close()

    total = len(ceps)
    print(f"[geocode_all] {total} CEPs pendentes (2006-2026)", flush=True)

    ok, falha = 0, 0
    for i, cep in enumerate(ceps, 1):
        resultado = geo.geocodificar_um(cep)
        geo._salvar_cache(cep, resultado)
        if resultado:
            ok += 1
        else:
            falha += 1
        if i % 100 == 0 or i == total:
            print(f"[geocode_all] {i}/{total} — ok={ok} falha={falha}", flush=True)
        time.sleep(0.15)

    print(f"[geocode_all] CONCLUÍDO — ok={ok} falha={falha}", flush=True)


if __name__ == "__main__":
    main()
