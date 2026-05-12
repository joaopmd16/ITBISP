"""
main.py — API FastAPI para o Dashboard ITBI-SP
Suporta SQLite (local) e PostgreSQL (produção).
"""
import os
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

import db as _db

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(title="Dashboard ITBI-SP", version="2.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

if FRONTEND_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


@app.on_event("startup")
def startup():
    _db.init_db()


def _get_filtros(logradouro=None, numero=None, bairro=None, cep=None,
                 ano_min=None, ano_max=None, valor_min=None, valor_max=None, natureza=None):
    return {k: v for k, v in {
        'logradouro': logradouro, 'numero': numero, 'bairro': bairro,
        'cep': cep, 'ano_min': ano_min, 'ano_max': ano_max,
        'valor_min': valor_min, 'valor_max': valor_max, 'natureza': natureza,
    }.items() if v}


def _build_where(filtros: dict) -> tuple:
    conds, params = [], []
    PH = _db.PH
    if filtros.get('logradouro'):
        conds.append(f"UPPER(logradouro) LIKE UPPER({PH})")
        params.append(f"%{filtros['logradouro']}%")
    if filtros.get('numero'):
        conds.append(f"numero = {PH}")
        params.append(filtros['numero'].strip())
    if filtros.get('bairro'):
        conds.append(f"UPPER(bairro) LIKE UPPER({PH})")
        params.append(f"%{filtros['bairro']}%")
    if filtros.get('cep'):
        conds.append(f"cep LIKE {PH}")
        params.append(f"{filtros['cep'].replace('-','')}%")
    if filtros.get('ano_min'):
        conds.append(f"ano_referencia >= {PH}")
        params.append(int(filtros['ano_min']))
    if filtros.get('ano_max'):
        conds.append(f"ano_referencia <= {PH}")
        params.append(int(filtros['ano_max']))
    if filtros.get('valor_min') is not None:
        conds.append(f"valor_declarado >= {PH}")
        params.append(float(filtros['valor_min']))
    if filtros.get('valor_max') is not None:
        conds.append(f"valor_declarado <= {PH}")
        params.append(float(filtros['valor_max']))
    if filtros.get('natureza'):
        conds.append(f"UPPER(natureza_transacao) LIKE UPPER({PH})")
        params.append(f"%{filtros['natureza']}%")
    return ("WHERE " + " AND ".join(conds)) if conds else "", params


@app.get("/")
def root():
    return {"status": "ok", "dashboard": "/app", "docs": "/docs"}


@app.get("/api/transacoes")
def buscar_transacoes(
    logradouro: Optional[str] = Query(None), numero: Optional[str] = Query(None),
    bairro: Optional[str] = Query(None), cep: Optional[str] = Query(None),
    ano_min: Optional[int] = Query(None), ano_max: Optional[int] = Query(None),
    valor_min: Optional[float] = Query(None), valor_max: Optional[float] = Query(None),
    natureza: Optional[str] = Query(None),
    sort: Optional[str] = Query("ano_referencia"), dir: Optional[str] = Query("desc"),
    pagina: int = Query(1, ge=1), por_pagina: int = Query(50, ge=1, le=500),
):
    COLS_OK = {"ano_referencia","mes_referencia","data_transacao","logradouro","numero",
               "bairro","valor_declarado","valor_financiado","valor_itbi",
               "area_terreno","area_construida","natureza_transacao"}
    sort_col = sort if sort in COLS_OK else "ano_referencia"
    sort_dir = "DESC" if dir != "asc" else "ASC"
    filtros = _get_filtros(logradouro, numero, bairro, cep, ano_min, ano_max, valor_min, valor_max, natureza)
    where, params = _build_where(filtros)
    offset = (pagina - 1) * por_pagina
    PH = _db.PH
    with _db.get_db() as conn:
        total = _db.fetchone(conn, f"SELECT COUNT(*) AS n FROM transacoes {where}", params)["n"]
        rows  = _db.fetchall(conn,
            f"SELECT * FROM transacoes {where} ORDER BY {sort_col} {sort_dir} NULLS LAST LIMIT {PH} OFFSET {PH}",
            params + [por_pagina, offset])
    return {"total": total, "pagina": pagina, "por_pagina": por_pagina,
            "paginas": (total + por_pagina - 1) // por_pagina, "dados": rows}


@app.get("/api/resumo")
def resumo(
    logradouro: Optional[str] = Query(None), numero: Optional[str] = Query(None),
    bairro: Optional[str] = Query(None), cep: Optional[str] = Query(None),
    ano_min: Optional[int] = Query(None), ano_max: Optional[int] = Query(None),
    valor_min: Optional[float] = Query(None), valor_max: Optional[float] = Query(None),
    natureza: Optional[str] = Query(None),
):
    filtros = _get_filtros(logradouro, numero, bairro, cep, ano_min, ano_max, valor_min, valor_max, natureza)
    where, params = _build_where(filtros)
    with _db.get_db() as conn:
        geral       = _db.fetchone(conn, f"SELECT COUNT(*) AS total_transacoes, SUM(valor_declarado) AS volume_total, AVG(valor_declarado) AS ticket_medio, MIN(valor_declarado) AS valor_minimo, MAX(valor_declarado) AS valor_maximo, SUM(valor_itbi) AS itbi_total FROM transacoes {where}", params)
        por_ano     = _db.fetchall(conn, f"SELECT ano_referencia, COUNT(*) AS transacoes, AVG(valor_declarado) AS ticket_medio, SUM(valor_declarado) AS volume FROM transacoes {where} GROUP BY ano_referencia ORDER BY ano_referencia", params)
        por_natureza= _db.fetchall(conn, f"SELECT natureza_transacao, COUNT(*) AS total FROM transacoes {where} GROUP BY natureza_transacao ORDER BY total DESC LIMIT 10", params)
        top_bairros = _db.fetchall(conn, f"SELECT bairro, COUNT(*) AS transacoes, AVG(valor_declarado) AS ticket_medio FROM transacoes {where} GROUP BY bairro ORDER BY transacoes DESC LIMIT 15", params)
    return {"geral": geral, "por_ano": por_ano, "por_natureza": por_natureza, "top_bairros": top_bairros}


@app.get("/api/autocomplete/logradouro")
def ac_logradouro(q: str = Query(..., min_length=3)):
    PH = _db.PH
    with _db.get_db() as conn:
        rows = _db.fetchall(conn, f"SELECT DISTINCT logradouro FROM transacoes WHERE UPPER(logradouro) LIKE UPPER({PH}) ORDER BY logradouro LIMIT 15", [f"%{q}%"])
    return [r["logradouro"] for r in rows if r.get("logradouro")]


@app.get("/api/autocomplete/bairro")
def ac_bairro(q: str = Query(..., min_length=2)):
    PH = _db.PH
    with _db.get_db() as conn:
        rows = _db.fetchall(conn, f"SELECT DISTINCT bairro FROM transacoes WHERE UPPER(bairro) LIKE UPPER({PH}) ORDER BY bairro LIMIT 15", [f"%{q}%"])
    return [r["bairro"] for r in rows if r.get("bairro")]


@app.get("/api/status")
def status():
    with _db.get_db() as conn:
        total = _db.fetchone(conn, "SELECT COUNT(*) AS n FROM transacoes")["n"]
        anos  = _db.fetchall(conn, "SELECT ano, linhas, updated_at FROM arquivos_processados ORDER BY ano DESC")
    return {"total_registros": total, "anos_processados": anos,
            "backend": "postgresql" if _db.USE_PG else "sqlite",
            "ultima_consulta": datetime.now().isoformat()}


@app.get("/api/exportar/excel")
def exportar_excel(ids: Optional[str] = Query(None),
    logradouro: Optional[str] = Query(None), numero: Optional[str] = Query(None),
    bairro: Optional[str] = Query(None), cep: Optional[str] = Query(None),
    ano_min: Optional[int] = Query(None), ano_max: Optional[int] = Query(None),
    valor_min: Optional[float] = Query(None), valor_max: Optional[float] = Query(None),
    natureza: Optional[str] = Query(None)):
    from fastapi.responses import Response
    from exportar import buscar, gerar_excel
    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()] if ids else None
    filtros = _get_filtros(logradouro, numero, bairro, cep, ano_min, ano_max, valor_min, valor_max, natureza)
    xls = gerar_excel(buscar(filtros, id_list), filtros)
    nome = f"ITBI_SP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(content=xls, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@app.get("/api/exportar/pdf")
def exportar_pdf(ids: Optional[str] = Query(None),
    logradouro: Optional[str] = Query(None), numero: Optional[str] = Query(None),
    bairro: Optional[str] = Query(None), cep: Optional[str] = Query(None),
    ano_min: Optional[int] = Query(None), ano_max: Optional[int] = Query(None),
    valor_min: Optional[float] = Query(None), valor_max: Optional[float] = Query(None),
    natureza: Optional[str] = Query(None)):
    from fastapi.responses import Response
    from exportar import buscar, gerar_pdf
    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()] if ids else None
    filtros = _get_filtros(logradouro, numero, bairro, cep, ano_min, ano_max, valor_min, valor_max, natureza)
    pdf = gerar_pdf(buscar(filtros, id_list), filtros)
    nome = f"ITBI_SP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return Response(content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@app.get("/api/mapa")
def mapa(ids: Optional[str] = Query(None),
    logradouro: Optional[str] = Query(None), numero: Optional[str] = Query(None),
    bairro: Optional[str] = Query(None), cep: Optional[str] = Query(None),
    ano_min: Optional[int] = Query(None), ano_max: Optional[int] = Query(None),
    valor_min: Optional[float] = Query(None), valor_max: Optional[float] = Query(None),
    natureza: Optional[str] = Query(None)):
    from geo import pontos_mapa
    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()] if ids else None
    filtros = _get_filtros(logradouro, numero, bairro, cep, ano_min, ano_max, valor_min, valor_max, natureza)
    return pontos_mapa(filtros, id_list)


@app.get("/api/mapa/status")
def mapa_status():
    from geo import status_geocoding
    return status_geocoding()


_sincronizando = False

@app.post("/api/sincronizar")
def sincronizar_endpoint(background_tasks: BackgroundTasks):
    global _sincronizando
    if _sincronizando:
        return JSONResponse({"status": "já rodando"}, status_code=409)
    def _run():
        global _sincronizando
        _sincronizando = True
        try:
            from scraper import sincronizar
            sincronizar()
        finally:
            _sincronizando = False
    background_tasks.add_task(_run)
    return {"status": "iniciado"}
