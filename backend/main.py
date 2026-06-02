"""
main.py — API do Dashboard ITBI-SP
Execute com:  uvicorn main:app --reload
Acesse:       http://localhost:8000
Docs:         http://localhost:8000/docs
"""

import sqlite3
import time
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
from datetime import datetime

from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

DB_PATH = Path(__file__).parent / "itbi.db"
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(title="Dashboard ITBI-SP", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



# ──────────────────────────────────────────────
# UTILITÁRIOS
# ──────────────────────────────────────────────

import unicodedata

def _unaccent(s: str | None) -> str | None:
    """Remove acentos e normaliza para uppercase — usado como função SQLite UNACCENT()."""
    if s is None:
        return None
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(s))
        if unicodedata.category(c) != 'Mn'
    ).upper()


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.create_function("UNACCENT", 1, _unaccent)   # disponível em todas as queries
    try:
        yield conn
    finally:
        conn.close()


def rows_to_list(rows) -> list[dict]:
    return [dict(r) for r in rows]


def _multi_like(col: str, value: str, nocase: bool = True) -> tuple[str, list]:
    """Suporte a múltiplos valores separados por vírgula → OR no SQL.
    Normaliza o INPUT (remove acentos) e compara com UPPER(col) —
    mantém uso dos índices sem chamar UDF por linha.
    """
    vals = [v.strip() for v in value.split(",") if v.strip()]
    if not vals:
        return "", []
    clauses = [f"UPPER({col}) LIKE ?" for _ in vals]
    return f"({' OR '.join(clauses)})", [f"%{_unaccent(v)}%" for v in vals]


@app.on_event("startup")
def startup():
    """Cria índices, ativa WAL e pré-aquece o cache do resumo."""
    # 1. Índices + WAL mode (muito mais rápido para leituras concorrentes)
    with get_db() as conn:
        conn.executescript("""
            PRAGMA journal_mode = WAL;
            PRAGMA cache_size   = -16384;
            PRAGMA temp_store   = MEMORY;
            PRAGMA mmap_size    = 67108864;
            CREATE INDEX IF NOT EXISTS idx_logradouro  ON transacoes(logradouro);
            CREATE INDEX IF NOT EXISTS idx_bairro      ON transacoes(bairro);
            CREATE INDEX IF NOT EXISTS idx_cep         ON transacoes(cep);
            CREATE INDEX IF NOT EXISTS idx_ano         ON transacoes(ano_referencia);
            CREATE INDEX IF NOT EXISTS idx_natureza    ON transacoes(natureza_transacao);
            CREATE INDEX IF NOT EXISTS idx_valor       ON transacoes(valor_declarado);
            CREATE INDEX IF NOT EXISTS idx_numero      ON transacoes(numero);
            CREATE INDEX IF NOT EXISTS idx_ano_mes     ON transacoes(ano_referencia, mes_referencia);
            CREATE INDEX IF NOT EXISTS idx_bairro_val  ON transacoes(bairro, valor_declarado);
            CREATE TABLE IF NOT EXISTS iptu (
                sql_terreno     TEXT PRIMARY KEY,
                tipo_uso        TEXT,
                descricao_uso   TEXT,
                padrao_iptu     TEXT,
                acc_iptu        TEXT,
                situacao_sql    TEXT,
                area_terreno    REAL,
                area_construida REAL,
                testada         REAL,
                fracao_ideal    TEXT,
                updated_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_iptu_sql ON iptu(sql_terreno);
        """)
        conn.commit()

    # 2. Pré-aquece o cache do resumo para o range padrão do frontend (últimos 3 anos)
    import threading
    def _prewarm():
        try:
            import time
            time.sleep(3)
            ano_max = datetime.now().year
            # Aquece os dois ranges mais usados: últimos 3 anos e último ano
            for ano_min in [ano_max - 2, ano_max]:
                where = "WHERE ano_referencia >= ? AND ano_referencia <= ?"
                params_q = [ano_min, ano_max]
                with get_db() as conn:
                    conn.execute("PRAGMA cache_size = -32768")
                    geral = conn.execute(f"""
                        SELECT COUNT(*) AS total_transacoes,
                               SUM(valor_declarado) AS volume_total,
                               AVG(valor_declarado) AS ticket_medio,
                               MIN(valor_declarado) AS valor_minimo,
                               MAX(valor_declarado) AS valor_maximo,
                               SUM(valor_itbi)      AS itbi_total
                        FROM transacoes {where}""", params_q).fetchone()
                    por_ano = conn.execute(f"""
                        SELECT ano_referencia, COUNT(*) as transacoes,
                               AVG(valor_declarado) as ticket_medio,
                               SUM(valor_declarado) as volume
                        FROM transacoes {where}
                        GROUP BY ano_referencia ORDER BY ano_referencia""", params_q).fetchall()
                    por_natureza = conn.execute(f"""
                        SELECT natureza_transacao, COUNT(*) as total
                        FROM transacoes {where}
                        GROUP BY natureza_transacao ORDER BY total DESC LIMIT 10""", params_q).fetchall()
                    top_bairros = conn.execute(f"""
                        SELECT bairro, COUNT(*) as transacoes,
                               AVG(valor_declarado) as ticket_medio
                        FROM transacoes {where}
                        GROUP BY bairro ORDER BY transacoes DESC LIMIT 15""", params_q).fetchall()
                resultado = {
                    "geral": dict(geral),
                    "por_ano": rows_to_list(por_ano),
                    "por_natureza": rows_to_list(por_natureza),
                    "top_bairros": rows_to_list(top_bairros),
                }
                _resumo_cache_set(where + str(params_q), resultado)
        except Exception:
            pass
    threading.Thread(target=_prewarm, daemon=True).start()

    # 3. Popula tabela iptu em background somente se estiver vazia
    def _popular_iptu_lazy():
        try:
            import time
            time.sleep(15)  # espera o servidor estabilizar
            with get_db() as conn:
                count = conn.execute("SELECT COUNT(*) FROM iptu").fetchone()[0]
            if count == 0:
                popular_iptu()
        except Exception:
            pass
    threading.Thread(target=_popular_iptu_lazy, daemon=True).start()


# ──────────────────────────────────────────────
# TABELA IPTU — normalização por imóvel
# ──────────────────────────────────────────────

def popular_iptu():
    """
    Popula/atualiza a tabela iptu com 1 linha por SQL (imóvel),
    usando os dados mais recentes da tabela transacoes.
    Executado em background no startup e após cada sincronização.
    """
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO iptu
                    (sql_terreno, tipo_uso, descricao_uso, padrao_iptu, acc_iptu,
                     situacao_sql, area_terreno, area_construida, testada, fracao_ideal, updated_at)
                SELECT
                    sql_terreno, tipo_uso, descricao_uso, padrao_iptu, acc_iptu,
                    situacao_sql, area_terreno, area_construida, testada, fracao_ideal,
                    datetime('now')
                FROM transacoes
                WHERE sql_terreno IS NOT NULL AND sql_terreno != ''
                GROUP BY sql_terreno
                HAVING rowid = MAX(rowid)
            """)
            conn.commit()
    except Exception:
        pass


# Cache simples em memória para /api/resumo
_resumo_cache: dict = {}

def _resumo_cache_get(key: str):
    entry = _resumo_cache.get(key)
    if entry and (time.time() - entry["ts"]) < 300:  # 5 min TTL
        return entry["data"]
    return None

def _resumo_cache_set(key: str, data: dict):
    _resumo_cache[key] = {"data": data, "ts": time.time()}


# ──────────────────────────────────────────────
# ROTAS
# ──────────────────────────────────────────────

@app.get("/api")
def root():
    return {"status": "ok", "docs": "/docs"}


# ── Busca de transações ──────────────────────

@app.get("/api/transacoes")
def buscar_transacoes(
    logradouro:  Optional[str]  = Query(None),
    numero:      Optional[str]  = Query(None),
    bairro:      Optional[str]  = Query(None),
    cep:         Optional[str]  = Query(None),
    sql:         Optional[str]  = Query(None),
    ano_min:     Optional[int]  = Query(None),
    ano_max:     Optional[int]  = Query(None),
    valor_min:   Optional[float]= Query(None),
    valor_max:   Optional[float]= Query(None),
    natureza:    Optional[str]  = Query(None),
    sort:        Optional[str]  = Query("ano_referencia"),
    dir:         Optional[str]  = Query("desc"),
    pagina:      int            = Query(1, ge=1),
    por_pagina:  int            = Query(50, ge=1, le=500),
):
    COLS_PERMITIDAS = {"ano_referencia","mes_referencia","data_transacao","logradouro",
                       "numero","bairro","valor_declarado","valor_financiado","valor_itbi",
                       "area_terreno","area_construida","natureza_transacao"}
    sort_col = sort if sort in COLS_PERMITIDAS else "ano_referencia"
    sort_dir = "DESC" if dir != "asc" else "ASC"

    filters = []
    params  = []
    if logradouro:
        cl, pr = _multi_like("logradouro", logradouro)
        filters.append(cl); params.extend(pr)
    if numero:
        filters.append("numero = ?")
        params.append(numero.strip())
    if bairro:
        cl, pr = _multi_like("bairro", bairro)
        filters.append(cl); params.extend(pr)
    if cep:
        cep_digits = ''.join(c for c in cep if c.isdigit()).zfill(8) if cep.strip() else ''
        if cep_digits:
            filters.append("REPLACE(REPLACE(cep,'-',''),' ','') LIKE ?")
            params.append(f"{cep_digits}%")
    if sql:
        # Remove pontuação para comparar só os dígitos
        sql_digits = ''.join(c for c in sql.strip() if c.isdigit())
        if sql_digits:
            filters.append("REPLACE(REPLACE(sql_terreno,'.',''),'-','') LIKE ?")
            params.append(f"%{sql_digits}%")
    if ano_min:
        filters.append("ano_referencia >= ?")
        params.append(ano_min)
    if ano_max:
        filters.append("ano_referencia <= ?")
        params.append(ano_max)
    if valor_min is not None:
        filters.append("valor_declarado >= ?")
        params.append(valor_min)
    if valor_max is not None:
        filters.append("valor_declarado <= ?")
        params.append(valor_max)
    if natureza:
        cl, pr = _multi_like("natureza_transacao", natureza)
        filters.append(cl); params.extend(pr)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    offset = (pagina - 1) * por_pagina

    with get_db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM transacoes {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM transacoes {where} ORDER BY {sort_col} {sort_dir} NULLS LAST LIMIT ? OFFSET ?",
            params + [por_pagina, offset]
        ).fetchall()

    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "paginas": (total + por_pagina - 1) // por_pagina,
        "dados": rows_to_list(rows),
    }


# ── Resumo / Estatísticas ────────────────────

@app.get("/api/resumo")
def resumo(
    logradouro: Optional[str]   = Query(None),
    numero:     Optional[str]   = Query(None),
    bairro:     Optional[str]   = Query(None),
    cep:        Optional[str]   = Query(None),
    sql:        Optional[str]   = Query(None),
    ano_min:    Optional[int]   = Query(None),
    ano_max:    Optional[int]   = Query(None),
    valor_min:  Optional[float] = Query(None),
    valor_max:  Optional[float] = Query(None),
    natureza:   Optional[str]   = Query(None),
):
    filters = []
    params  = []
    if logradouro:
        cl, pr = _multi_like("logradouro", logradouro)
        filters.append(cl); params.extend(pr)
    if numero:
        filters.append("numero = ?")
        params.append(numero.strip())
    if bairro:
        cl, pr = _multi_like("bairro", bairro)
        filters.append(cl); params.extend(pr)
    if cep:
        cep_digits = ''.join(c for c in cep if c.isdigit()).zfill(8) if cep.strip() else ''
        if cep_digits:
            filters.append("REPLACE(REPLACE(cep,'-',''),' ','') LIKE ?")
            params.append(f"{cep_digits}%")
    if sql:
        sql_digits = ''.join(c for c in sql.strip() if c.isdigit())
        if sql_digits:
            filters.append("REPLACE(REPLACE(sql_terreno,'.',''),'-','') LIKE ?")
            params.append(f"%{sql_digits}%")
    if ano_min:
        filters.append("ano_referencia >= ?")
        params.append(ano_min)
    if ano_max:
        filters.append("ano_referencia <= ?")
        params.append(ano_max)
    if valor_min is not None:
        filters.append("valor_declarado >= ?")
        params.append(valor_min)
    if valor_max is not None:
        filters.append("valor_declarado <= ?")
        params.append(valor_max)
    if natureza:
        cl, pr = _multi_like("natureza_transacao", natureza)
        filters.append(cl); params.extend(pr)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    # Cache: mesmos filtros → resposta instantânea por 5 min
    cache_key = where + str(params)
    cached = _resumo_cache_get(cache_key)
    if cached:
        return cached

    with get_db() as conn:
        conn.execute("PRAGMA cache_size = -64000")   # 64 MB page cache
        conn.execute("PRAGMA temp_store = MEMORY")

        geral = conn.execute(f"""
            SELECT
                COUNT(*)           AS total_transacoes,
                SUM(valor_declarado) AS volume_total,
                AVG(valor_declarado) AS ticket_medio,
                MIN(valor_declarado) AS valor_minimo,
                MAX(valor_declarado) AS valor_maximo,
                SUM(valor_itbi)      AS itbi_total
            FROM transacoes {where}
        """, params).fetchone()

        por_ano = conn.execute(f"""
            SELECT ano_referencia,
                   COUNT(*) as transacoes,
                   AVG(valor_declarado) as ticket_medio,
                   SUM(valor_declarado) as volume
            FROM transacoes {where}
            GROUP BY ano_referencia
            ORDER BY ano_referencia
        """, params).fetchall()

        por_natureza = conn.execute(f"""
            SELECT natureza_transacao, COUNT(*) as total
            FROM transacoes {where}
            GROUP BY natureza_transacao
            ORDER BY total DESC
            LIMIT 10
        """, params).fetchall()

        top_bairros = conn.execute(f"""
            SELECT bairro,
                   COUNT(*) as transacoes,
                   AVG(valor_declarado) as ticket_medio
            FROM transacoes {where}
            GROUP BY bairro
            ORDER BY transacoes DESC
            LIMIT 15
        """, params).fetchall()

        where_and = ("WHERE" if not filters else "AND")
        por_mes = conn.execute(f"""
            SELECT ano_referencia, mes_referencia, COUNT(*) as transacoes
            FROM transacoes {where}
            {where_and} mes_referencia IS NOT NULL
            GROUP BY ano_referencia, mes_referencia
            ORDER BY ano_referencia, mes_referencia
        """, params).fetchall()

        faixas_valor = conn.execute(f"""
            SELECT
              CASE
                WHEN valor_declarado <  300000  THEN 'Ate 300k'
                WHEN valor_declarado <  600000  THEN '300k-600k'
                WHEN valor_declarado < 1000000  THEN '600k-1M'
                WHEN valor_declarado < 2000000  THEN '1M-2M'
                ELSE 'Acima 2M'
              END AS faixa,
              COUNT(*) AS transacoes,
              MIN(valor_declarado) AS _ord
            FROM transacoes {where}
            {where_and} valor_declarado IS NOT NULL AND valor_declarado > 0
            GROUP BY faixa
            ORDER BY _ord
        """, params).fetchall()

    resultado = {
        "geral": dict(geral),
        "por_ano": rows_to_list(por_ano),
        "por_natureza": rows_to_list(por_natureza),
        "top_bairros": rows_to_list(top_bairros),
        "por_mes": rows_to_list(por_mes),
        "faixas_valor": [{"faixa": r["faixa"], "transacoes": r["transacoes"]} for r in faixas_valor],
    }
    _resumo_cache_set(cache_key, resultado)
    return resultado


# ── Autocomplete ─────────────────────────────

@app.get("/api/autocomplete/logradouro")
def autocomplete_logradouro(q: str = Query(..., min_length=3)):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT DISTINCT logradouro FROM transacoes
            WHERE UPPER(logradouro) LIKE ?
            ORDER BY logradouro LIMIT 15
        """, (f"%{_unaccent(q)}%",)).fetchall()
    return [r["logradouro"] for r in rows if r["logradouro"]]


@app.get("/api/autocomplete/bairro")
def autocomplete_bairro(q: str = Query(..., min_length=2)):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT DISTINCT bairro FROM transacoes
            WHERE UPPER(bairro) LIKE ?
            ORDER BY bairro LIMIT 15
        """, (f"%{_unaccent(q)}%",)).fetchall()
    return [r["bairro"] for r in rows if r["bairro"]]


# ── Exportação ───────────────────────────────

def _get_filtros(logradouro=None, numero=None, bairro=None, cep=None,
                 ano_min=None, ano_max=None, valor_min=None, valor_max=None, natureza=None):
    return {k: v for k, v in {
        'logradouro': logradouro, 'numero': numero, 'bairro': bairro,
        'cep': cep, 'ano_min': ano_min, 'ano_max': ano_max,
        'valor_min': valor_min, 'valor_max': valor_max, 'natureza': natureza,
    }.items() if v}


EXPORT_PARAMS = [
    ("ids",        Optional[str],   Query(None)),
    ("logradouro", Optional[str],   Query(None)),
    ("numero",     Optional[str],   Query(None)),
    ("bairro",     Optional[str],   Query(None)),
    ("cep",        Optional[str],   Query(None)),
    ("ano_min",    Optional[int],   Query(None)),
    ("ano_max",    Optional[int],   Query(None)),
    ("valor_min",  Optional[float], Query(None)),
    ("valor_max",  Optional[float], Query(None)),
    ("natureza",   Optional[str],   Query(None)),
]


COLS_EXPORT_PERMITIDAS = {
    "ano_referencia","mes_referencia","data_transacao","logradouro","numero",
    "bairro","valor_declarado","valor_financiado","valor_itbi","area_terreno",
    "area_construida","natureza_transacao","cep","sql_terreno",
}

@app.get("/api/exportar/excel")
def exportar_excel(
    ids: Optional[str] = Query(None),
    logradouro: Optional[str] = Query(None),
    numero: Optional[str] = Query(None),
    bairro: Optional[str] = Query(None),
    cep: Optional[str] = Query(None),
    ano_min: Optional[int] = Query(None),
    ano_max: Optional[int] = Query(None),
    valor_min: Optional[float] = Query(None),
    valor_max: Optional[float] = Query(None),
    natureza: Optional[str] = Query(None),
    sort: Optional[str] = Query("ano_referencia"),
    dir: Optional[str] = Query("desc"),
):
    from fastapi.responses import Response
    from exportar import buscar, gerar_excel
    sort_col = sort if sort in COLS_EXPORT_PERMITIDAS else "ano_referencia"
    sort_dir = "DESC" if dir != "asc" else "ASC"
    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()] if ids else None
    filtros = _get_filtros(logradouro, numero, bairro, cep, ano_min, ano_max, valor_min, valor_max, natureza)
    df = buscar(filtros, id_list, sort_col=sort_col, sort_dir=sort_dir)
    xls = gerar_excel(df, filtros)
    nome = f"ITBI_SP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(content=xls,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@app.get("/api/exportar/pdf")
def exportar_pdf(
    ids: Optional[str] = Query(None),
    logradouro: Optional[str] = Query(None),
    numero: Optional[str] = Query(None),
    bairro: Optional[str] = Query(None),
    cep: Optional[str] = Query(None),
    ano_min: Optional[int] = Query(None),
    ano_max: Optional[int] = Query(None),
    valor_min: Optional[float] = Query(None),
    valor_max: Optional[float] = Query(None),
    natureza: Optional[str] = Query(None),
    sort: Optional[str] = Query("ano_referencia"),
    dir: Optional[str] = Query("desc"),
):
    from fastapi.responses import Response
    from exportar import buscar, gerar_pdf
    sort_col = sort if sort in COLS_EXPORT_PERMITIDAS else "ano_referencia"
    sort_dir = "DESC" if dir != "asc" else "ASC"
    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()] if ids else None
    filtros = _get_filtros(logradouro, numero, bairro, cep, ano_min, ano_max, valor_min, valor_max, natureza)
    df = buscar(filtros, id_list, sort_col=sort_col, sort_dir=sort_dir)
    pdf = gerar_pdf(df, filtros)
    nome = f"ITBI_SP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return Response(content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'})


# ── IPTU por imóvel ──────────────────────────

@app.get("/api/iptu/{sql_terreno}")
def get_iptu(sql_terreno: str):
    """Retorna dados IPTU cadastrais do imóvel pelo número SQL."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM iptu WHERE sql_terreno = ?", (sql_terreno,)
        ).fetchone()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="SQL não encontrado na tabela IPTU")
    return dict(row)


# ── Status do banco ───────────────────────────

@app.get("/api/status")
def status():
    if not DB_PATH.exists():
        return {"banco": "não inicializado", "total_registros": 0, "anos": []}
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM transacoes").fetchone()[0]
        anos  = conn.execute("""
            SELECT ap.ano, ap.linhas, ap.updated_at
            FROM arquivos_processados ap
            ORDER BY ap.ano DESC
        """).fetchall()
    return {
        "banco": str(DB_PATH),
        "total_registros": total,
        "anos_processados": rows_to_list(anos),
        "ultima_consulta": datetime.now().isoformat(),
    }


# ── Mapa ──────────────────────────────────────

# ── Mapa desativado temporariamente (in development) ──────────
# @app.get("/api/mapa")
# @app.get("/api/mapa/status")


# ── Sincronização (trigger manual/cron) ──────

sincronizando = False
_sync_log: list[str] = []
_sync_inicio: Optional[float] = None

@app.get("/api/sincronizar/status")
def sincronizar_status():
    return {
        "rodando": sincronizando,
        "log": _sync_log[-30:],   # últimas 30 linhas
        "inicio": _sync_inicio,
    }

@app.post("/api/sincronizar")
def sincronizar(background_tasks: BackgroundTasks, anos: Optional[str] = Query(None)):
    """Dispara a sincronização em background. Use com cron ou botão no dashboard."""
    global sincronizando, _sync_log, _sync_inicio
    if sincronizando:
        return JSONResponse({"status": "já rodando"}, status_code=409)

    anos_list = [int(a) for a in anos.split(",") if a.strip().isdigit()] if anos else None

    def _run():
        global sincronizando, _sync_log, _sync_inicio
        import time, sys, io, contextlib
        sincronizando = True
        _sync_inicio = time.time()
        _sync_log.clear()

        class _Tee:
            def write(self, s):
                if s.strip():
                    _sync_log.append(s.rstrip())
            def flush(self): pass

        tee = _Tee()
        try:
            with contextlib.redirect_stdout(tee), contextlib.redirect_stderr(tee):
                from scraper_csv import sincronizar as _sync
                # forcar=True → re-baixa o XLSX mesmo que já exista em cache
                _sync(anos=anos_list, forcar=True)
                _sync_log.append("✅ Scraper concluído. Atualizando tabela IPTU…")
                popular_iptu()
                _sync_log.append("✅ Sincronização completa!")
                _resumo_cache.clear()
        except Exception as e:
            _sync_log.append(f"❌ Erro: {e}")
        finally:
            sincronizando = False

    background_tasks.add_task(_run)
    return {"status": "iniciado", "anos": anos_list or "todos"}


# Serve o frontend estático (deve ficar no final para não sobrescrever as rotas da API)
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
