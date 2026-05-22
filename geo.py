"""
geo.py — Geocodifica CEPs com cache SQLite, não-bloqueante.
Fontes: BrasilAPI → Nominatim (fallback)
"""
import time
import threading
import requests
import db as _db

HEADERS = {"User-Agent": "ITBI-Dashboard/1.0 (contato@itbi-dashboard.local)"}

# Thread de background
_geo_thread: threading.Thread | None = None
_geo_status = {"rodando": False, "pendentes": 0, "ok": 0, "falha": 0}


# ──────────────────────────────────────────────
# INIT
# ──────────────────────────────────────────────

def init_geo_cache():
    _db.init_db()  # garante tabelas criadas


# ──────────────────────────────────────────────
# GEOCODING — fontes com fallback
# ──────────────────────────────────────────────

def _via_brasilapi(cep: str) -> dict | None:
    try:
        r = requests.get(
            f"https://brasilapi.com.br/api/cep/v2/{cep}",
            headers=HEADERS, timeout=6
        )
        if r.status_code == 200:
            d = r.json()
            lat = d.get("location", {}).get("coordinates", {}).get("latitude")
            lng = d.get("location", {}).get("coordinates", {}).get("longitude")
            if lat and lng:
                return {"lat": float(lat), "lng": float(lng),
                        "bairro": d.get("neighborhood",""), "fonte": "brasilapi"}
    except Exception:
        pass
    return None


# Bounding box de São Paulo cidade (aproximado)
SP_BOUNDS = {"lat_min": -24.01, "lat_max": -23.35, "lng_min": -46.83, "lng_max": -46.36}

def _dentro_de_sp(lat: float, lng: float) -> bool:
    """Verifica se as coordenadas estão dentro do município de São Paulo."""
    return (SP_BOUNDS["lat_min"] <= lat <= SP_BOUNDS["lat_max"] and
            SP_BOUNDS["lng_min"] <= lng <= SP_BOUNDS["lng_max"])


def _via_nominatim(cep: str) -> dict | None:
    """Geocodifica via Nominatim com validação de bounding box de SP."""
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": f"{cep[:5]}-{cep[5:]} São Paulo SP",
                "format": "json",
                "limit": 3,
                "countrycodes": "br",
                "viewbox": "-47.0,-24.1,-46.3,-23.3",
                "bounded": 1,
            },
            headers=HEADERS, timeout=8
        )
        if r.status_code == 200:
            data = r.json()
            for item in data:
                lat = float(item["lat"])
                lng = float(item["lon"])
                if _dentro_de_sp(lat, lng):
                    return {"lat": lat, "lng": lng, "bairro": "", "fonte": "nominatim"}
    except Exception:
        pass
    return None


def geocodificar_um(cep: str) -> dict | None:
    """Tenta BrasilAPI primeiro, depois Nominatim."""
    geo = _via_brasilapi(cep)
    if not geo:
        time.sleep(0.3)  # respeita rate limit do Nominatim
        geo = _via_nominatim(cep)
    return geo


# ──────────────────────────────────────────────
# CACHE — leitura e escrita
# ──────────────────────────────────────────────

def _cep_limpo(cep: str) -> str:
    return cep.replace("-","").replace(".","").strip().zfill(8)


def _ler_cache(conn, cep: str) -> dict | None:
    row = _db.fetchone(conn, f"SELECT lat, lng, bairro, ok FROM geo_cache WHERE cep = {_db.PH}", [cep])
    if not row:
        return None
    if row["ok"] == 0:
        return {"erro": True}
    if row["lat"] is None:
        return None
    return {"lat": row["lat"], "lng": row["lng"], "bairro": row["bairro"] or ""}


def _salvar_cache(cep: str, geo: dict | None):
    PH = _db.PH
    with _db.get_db() as conn:
        if geo:
            if _db.USE_PG:
                _db.execute(conn, f"""
                    INSERT INTO geo_cache (cep, lat, lng, bairro, ok, fonte)
                    VALUES ({PH},{PH},{PH},{PH},1,{PH})
                    ON CONFLICT (cep) DO UPDATE SET lat={PH}, lng={PH}, bairro={PH}, ok=1, fonte={PH}
                """, [cep, geo["lat"], geo["lng"], geo.get("bairro",""), geo.get("fonte",""),
                      geo["lat"], geo["lng"], geo.get("bairro",""), geo.get("fonte","")])
            else:
                _db.execute(conn, f"INSERT OR REPLACE INTO geo_cache (cep, lat, lng, bairro, ok, fonte) VALUES ({PH},{PH},{PH},{PH},1,{PH})",
                    [cep, geo["lat"], geo["lng"], geo.get("bairro",""), geo.get("fonte","")])
        else:
            if _db.USE_PG:
                _db.execute(conn, f"INSERT INTO geo_cache (cep, lat, lng, bairro, ok) VALUES ({PH},NULL,NULL,'',0) ON CONFLICT (cep) DO UPDATE SET ok=0", [cep])
            else:
                _db.execute(conn, f"INSERT OR REPLACE INTO geo_cache (cep, lat, lng, bairro, ok) VALUES ({PH},NULL,NULL,'',0)", [cep])


# ──────────────────────────────────────────────
# GEOCODING EM BACKGROUND
# ──────────────────────────────────────────────

def _worker(ceps: list[str]):
    global _geo_status
    _geo_status = {"rodando": True, "pendentes": len(ceps), "ok": 0, "falha": 0}
    for cep in ceps:
        geo = geocodificar_um(cep)
        _salvar_cache(cep, geo)
        if geo:
            _geo_status["ok"] += 1
        else:
            _geo_status["falha"] += 1
        _geo_status["pendentes"] -= 1
        time.sleep(0.15)  # rate limiting
    _geo_status["rodando"] = False


def iniciar_geocoding_background(ceps: list[str]):
    global _geo_thread
    if _geo_thread and _geo_thread.is_alive():
        return  # já rodando
    if not ceps:
        return
    _geo_thread = threading.Thread(target=_worker, args=(ceps,), daemon=True)
    _geo_thread.start()


def status_geocoding() -> dict:
    return dict(_geo_status)


# ──────────────────────────────────────────────
# PONTOS DO MAPA — não-bloqueante
# ──────────────────────────────────────────────

def pontos_mapa(filtros: dict, ids: list = None, max_ceps: int = 2000) -> dict:
    """
    Retorna pontos que JÁ estão geocodificados (cache).
    Dispara geocoding em background para os que faltam.
    """
    init_geo_cache()

    PH = _db.PH
    conds, params = [], []
    if ids:
        ph = ','.join([PH] * len(ids))
        conds.append(f"t.id IN ({ph})")
        params.extend(ids)
    else:
        if filtros.get('logradouro'):
            conds.append(f"UPPER(t.logradouro) LIKE UPPER({PH})")
            params.append(f"%{filtros['logradouro']}%")
        if filtros.get('bairro'):
            conds.append(f"UPPER(t.bairro) LIKE UPPER({PH})")
            params.append(f"%{filtros['bairro']}%")
        if filtros.get('cep'):
            conds.append(f"t.cep LIKE {PH}")
            params.append(f"{filtros['cep'].replace('-','')}%")
        if filtros.get('ano_min'):
            conds.append(f"t.ano_referencia >= {PH}")
            params.append(int(filtros['ano_min']))
        if filtros.get('ano_max'):
            conds.append(f"t.ano_referencia <= {PH}")
            params.append(int(filtros['ano_max']))
        if filtros.get('valor_min'):
            conds.append(f"t.valor_declarado >= {PH}")
            params.append(float(filtros['valor_min']))
        if filtros.get('valor_max'):
            conds.append(f"t.valor_declarado <= {PH}")
            params.append(float(filtros['valor_max']))

    base_where = ("AND " + " AND ".join(conds)) if conds else ""
    with _db.get_db() as conn:
        rows = _db.fetchall(conn, f"""
            SELECT
                REPLACE(t.cep, '-', '') AS cep_clean,
                MAX(t.bairro) AS bairro_db,
                COUNT(*) AS total,
                AVG(t.valor_declarado) AS avg_valor,
                MAX(t.valor_declarado) AS max_valor,
                SUM(t.valor_declarado) AS sum_valor,
                g.lat, g.lng,
                COALESCE(g.bairro, '') AS bairro_geo,
                g.ok
            FROM transacoes t
            LEFT JOIN geo_cache g ON g.cep = REPLACE(t.cep, '-', '')
            WHERE t.cep IS NOT NULL AND t.cep != '' {base_where}
            GROUP BY cep_clean, g.lat, g.lng, g.bairro, g.ok
            ORDER BY total DESC
            LIMIT {max_ceps}
        """, params)

    pontos = []
    sem_geo = []

    for r in rows:
        cep = r["cep_clean"]
        if not cep:
            continue

        if r["lat"] and r["lng"]:
            pontos.append({
                "cep":       cep,
                "lat":       r["lat"],
                "lng":       r["lng"],
                "bairro":    r["bairro_db"] or r["bairro_geo"] or "",
                "count":     r["total"],
                "avg_valor": round(r["avg_valor"] or 0),
                "max_valor": round(r["max_valor"] or 0),
                "sum_valor": round(r["sum_valor"] or 0),
            })
        elif r.get("ok") is None:  # nunca tentou geocodificar
            sem_geo.append(cep)

    # Dispara geocoding em background para os sem coordenadas
    if sem_geo:
        iniciar_geocoding_background(sem_geo[:500])

    return {
        "pontos": pontos,
        "total_ceps": len(rows),
        "geocodificados": len(pontos),
        "pendentes": len(sem_geo),
        "geo_status": status_geocoding(),
    }
