"""
debug_colunas.py — Mostra os nomes reais das colunas das planilhas no banco.
Execute: python debug_colunas.py
"""
import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent / "itbi.db"
CACHE_DIR = Path(__file__).parent / "cache"

# ── 1. Ver o que está no banco ──────────────────────────────────
print("=" * 60)
print("DADOS NO BANCO")
print("=" * 60)
conn = sqlite3.connect(DB_PATH)

total = conn.execute("SELECT COUNT(*) FROM transacoes").fetchone()[0]
print(f"Total de registros: {total:,}")

# Amostra de linhas
df = pd.read_sql("SELECT * FROM transacoes LIMIT 5", conn)
print("\nColunas no banco:")
print(df.dtypes.to_string())
print("\nAmostra de dados:")
print(df.to_string())

# Quais colunas têm dados
print("\n\nPREENCHIMENTO DE CADA COLUNA:")
for col in df.columns:
    preenchido = conn.execute(
        f"SELECT COUNT(*) FROM transacoes WHERE {col} IS NOT NULL AND {col} != ''"
    ).fetchone()[0]
    pct = preenchido / total * 100 if total else 0
    status = "✅" if pct > 50 else ("⚠️" if pct > 0 else "❌")
    print(f"  {status} {col:<25} {preenchido:>10,} ({pct:.1f}%)")

conn.close()

# ── 2. Ver colunas RAW dos xlsx ─────────────────────────────────
print("\n" + "=" * 60)
print("COLUNAS ORIGINAIS DOS XLSX (primeiros 3 anos disponíveis)")
print("=" * 60)

xlsx_files = sorted(CACHE_DIR.glob("*.xlsx"), reverse=True)[:3]
if not xlsx_files:
    print("Nenhum arquivo xlsx em cache encontrado.")
else:
    for f in xlsx_files:
        print(f"\n📄 {f.name}")
        xl = pd.ExcelFile(f)
        for sheet in xl.sheet_names[:3]:  # primeiras 3 abas
            try:
                df_raw = xl.parse(sheet, nrows=2)
                if df_raw.empty: continue
                print(f"  Aba '{sheet}':")
                for col in df_raw.columns:
                    print(f"    → '{col}'")
            except:
                pass
