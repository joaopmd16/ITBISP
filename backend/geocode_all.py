"""
geocode_all.py — Geocodifica TODOS os CEPs distintos (2006-2026) de uma vez,
salvando no cache SQLite (geo_cache). Roda standalone via nohup na VM,
independente de acesso ao site. Idempotente: pula CEPs já no cache.

Suporta sharding para rodar em paralelo:
    python3 geocode_all.py <shard_id> <total_shards>
Ex: 3 processos em paralelo, cada um pega 1/3 dos CEPs pendentes:
    python3 geocode_all.py 0 3
    python3 geocode_all.py 1 3
    python3 geocode_all.py 2 3
"""
import sqlite3
import sys
import time
from pathlib import Path

import geo

DB_PATH = Path(__file__).parent / "itbi.db"


def main():
    shard_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    total_shards = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    tag = f"[geocode_all shard {shard_id}/{total_shards}]"

    geo.init_geo_cache()
    conn = sqlite3.connect(DB_PATH)

    todos = [(r[0], r[1] or "", r[2] or "") for r in conn.execute("""
        SELECT REPLACE(t.cep, '-', '') AS cep_clean, MAX(t.logradouro), MAX(t.bairro)
        FROM transacoes t
        LEFT JOIN geo_cache g ON g.cep = REPLACE(t.cep, '-', '')
        WHERE t.cep IS NOT NULL AND t.cep != '' AND g.cep IS NULL
        GROUP BY cep_clean
    """).fetchall()]
    conn.close()

    itens = [c for i, c in enumerate(todos) if i % total_shards == shard_id]

    total = len(itens)
    print(f"{tag} {total} CEPs pendentes neste shard", flush=True)

    ok, falha = 0, 0
    for i, (cep, logradouro, bairro) in enumerate(itens, 1):
        resultado = geo.geocodificar_um(cep, logradouro, bairro)
        geo._salvar_cache(cep, resultado)
        if resultado:
            ok += 1
        else:
            falha += 1
        if i % 100 == 0 or i == total:
            print(f"{tag} {i}/{total} — ok={ok} falha={falha}", flush=True)
        time.sleep(0.15)

    print(f"{tag} CONCLUÍDO — ok={ok} falha={falha}", flush=True)


if __name__ == "__main__":
    main()
