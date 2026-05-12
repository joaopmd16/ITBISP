"""
db.py — Abstração de banco de dados.
  - LOCAL:      SQLite  (sem DATABASE_URL)
  - PRODUÇÃO:   PostgreSQL (com DATABASE_URL no ambiente)
"""
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# ── Detecta ambiente ───────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Railway às vezes usa "postgres://" — psycopg2 precisa de "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

USE_PG  = bool(DATABASE_URL and "postgresql" in DATABASE_URL)
DB_PATH = Path(__file__).parent / "itbi.db"

PH = "%s" if USE_PG else "?"   # placeholder de query


# ── Conexão ────────────────────────────────────────────────────
@contextmanager
def get_db():
    if USE_PG:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def execute(conn, sql: str, params=None):
    """Executa uma query com placeholder correto (?  ou %s)."""
    if params is None:
        params = []
    # Converte ? → %s se necessário
    if USE_PG:
        sql = sql.replace("?", "%s")
    if USE_PG:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur
    else:
        return conn.execute(sql, params)


def fetchall(conn, sql: str, params=None) -> list[dict]:
    cur = execute(conn, sql, params or [])
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def fetchone(conn, sql: str, params=None) -> dict | None:
    cur = execute(conn, sql, params or [])
    row = cur.fetchone()
    return dict(row) if row else None


# ── Init / Migrations ──────────────────────────────────────────

def _col_exists(conn, table: str, col: str) -> bool:
    if USE_PG:
        r = fetchone(conn,
            "SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
            [table, col])
        return r is not None
    else:
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        return col in cols


def _add_col_if_missing(conn, table: str, col: str, tipo: str):
    if not _col_exists(conn, table, col):
        execute(conn, f"ALTER TABLE {col} ADD COLUMN {col} {tipo}")


def init_db():
    """Cria tabelas e aplica migrações."""
    with get_db() as conn:
        if USE_PG:
            _init_pg(conn)
        else:
            _init_sqlite(conn)
    print(f"✅ Banco pronto ({'PostgreSQL' if USE_PG else 'SQLite'})")


def _init_sqlite(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            ano_referencia        INTEGER,
            mes_referencia        INTEGER,
            data_transacao        TEXT,
            logradouro            TEXT,
            numero                TEXT,
            complemento           TEXT,
            bairro                TEXT,
            cep                   TEXT,
            sql_terreno           TEXT,
            area_terreno          REAL,
            area_construida       REAL,
            valor_declarado       REAL,
            valor_financiado      REAL,
            valor_itbi            REAL,
            valor_venal_ref       REAL,
            proporcao_transmitida REAL,
            natureza_transacao    TEXT,
            tipo_financiamento    TEXT,
            tipo_uso              TEXT,
            descricao_uso         TEXT,
            acc_iptu              TEXT,
            cartorio_registro     TEXT,
            matricula_imovel      TEXT,
            situacao_sql          TEXT,
            testada               REAL,
            fracao_ideal          TEXT,
            padrao_iptu           TEXT,
            created_at            TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS arquivos_processados (
            ano        INTEGER PRIMARY KEY,
            hash       TEXT,
            linhas     INTEGER,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS geo_cache (
            cep        TEXT PRIMARY KEY,
            lat        REAL,
            lng        REAL,
            bairro     TEXT,
            ok         INTEGER DEFAULT 1,
            fonte      TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    # Índices
    for idx, col in [
        ("idx_logradouro", "logradouro"),
        ("idx_bairro",     "bairro"),
        ("idx_ano",        "ano_referencia"),
        ("idx_mes",        "mes_referencia"),
        ("idx_cep",        "cep"),
    ]:
        conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON transacoes({col})")

    # Migração: colunas adicionadas em versões posteriores
    todas = [
        ("descricao_uso",        "TEXT"),  ("proporcao_transmitida", "REAL"),
        ("tipo_financiamento",   "TEXT"),  ("acc_iptu",              "TEXT"),
        ("valor_venal_ref",      "REAL"),  ("cartorio_registro",     "TEXT"),
        ("matricula_imovel",     "TEXT"),  ("situacao_sql",          "TEXT"),
        ("testada",              "REAL"),  ("fracao_ideal",          "TEXT"),
        ("padrao_iptu",          "TEXT"),
    ]
    cols = {r[1] for r in conn.execute("PRAGMA table_info(transacoes)")}
    for nome, tipo in todas:
        if nome not in cols:
            conn.execute(f"ALTER TABLE transacoes ADD COLUMN {nome} {tipo}")
            print(f"   🔧 Coluna adicionada: {nome}")

    geo_cols = {r[1] for r in conn.execute("PRAGMA table_info(geo_cache)")}
    for nome, tipo in [("fonte", "TEXT"), ("updated_at", "TEXT")]:
        if nome not in geo_cols:
            conn.execute(f"ALTER TABLE geo_cache ADD COLUMN {nome} {tipo}")


def _init_pg(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id                    SERIAL PRIMARY KEY,
            ano_referencia        INTEGER,
            mes_referencia        INTEGER,
            data_transacao        TEXT,
            logradouro            TEXT,
            numero                TEXT,
            complemento           TEXT,
            bairro                TEXT,
            cep                   TEXT,
            sql_terreno           TEXT,
            area_terreno          REAL,
            area_construida       REAL,
            valor_declarado       REAL,
            valor_financiado      REAL,
            valor_itbi            REAL,
            valor_venal_ref       REAL,
            proporcao_transmitida REAL,
            natureza_transacao    TEXT,
            tipo_financiamento    TEXT,
            tipo_uso              TEXT,
            descricao_uso         TEXT,
            acc_iptu              TEXT,
            cartorio_registro     TEXT,
            matricula_imovel      TEXT,
            situacao_sql          TEXT,
            testada               REAL,
            fracao_ideal          TEXT,
            padrao_iptu           TEXT,
            created_at            TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS arquivos_processados (
            ano        INTEGER PRIMARY KEY,
            hash       TEXT,
            linhas     INTEGER,
            updated_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS geo_cache (
            cep        TEXT PRIMARY KEY,
            lat        REAL,
            lng        REAL,
            bairro     TEXT,
            ok         INTEGER DEFAULT 1,
            fonte      TEXT,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    for idx, col in [
        ("idx_logradouro", "logradouro"),
        ("idx_bairro",     "bairro"),
        ("idx_ano",        "ano_referencia"),
        ("idx_mes",        "mes_referencia"),
        ("idx_cep",        "cep"),
    ]:
        cur.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON transacoes({col})")

    # Adiciona colunas que possam faltar
    todas = [
        ("valor_venal_ref","REAL"), ("cartorio_registro","TEXT"),
        ("matricula_imovel","TEXT"), ("situacao_sql","TEXT"),
        ("testada","REAL"), ("fracao_ideal","TEXT"), ("padrao_iptu","TEXT"),
        ("tipo_financiamento","TEXT"), ("acc_iptu","TEXT"),
    ]
    for nome, tipo in todas:
        cur.execute(f"""
            ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS {nome} {tipo}
        """)
    cur.execute("ALTER TABLE geo_cache ADD COLUMN IF NOT EXISTS fonte TEXT")
