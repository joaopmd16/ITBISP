"""
geo.py — Geocodifica CEPs com cache SQLite, não-bloqueante.
Fontes: BrasilAPI → Nominatim (fallback)
"""
import logging
import time
import sqlite3
import threading
import requests
from pathlib import Path

logger = logging.getLogger("itbi")

DB_PATH = Path(__file__).parent / "itbi.db"
HEADERS = {"User-Agent": "ITBI-Dashboard/1.0 (contato@itbi-dashboard.local)"}

# Thread de background
_geo_thread: threading.Thread | None = None
_geo_status = {"rodando": False, "pendentes": 0, "ok": 0, "falha": 0}


# ──────────────────────────────────────────────
# INIT
# ──────────────────────────────────────────────

def init_geo_cache():
    conn = sqlite3.connect(DB_PATH)
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
    # Migração: adiciona colunas que podem faltar em tabelas antigas
    cols = {r[1] for r in conn.execute("PRAGMA table_info(geo_cache)")}
    for col, tipo in [("fonte", "TEXT"), ("updated_at", "TEXT")]:
        if col not in cols:
            conn.execute(f"ALTER TABLE geo_cache ADD COLUMN {col} {tipo}")
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# GEOCODING — fontes com fallback
# ──────────────────────────────────────────────

# Bounding box de São Paulo cidade (aproximado) — só uma triagem grosseira e barata
# ANTES da checagem forte por nome de município (ver _e_municipio_sao_paulo). Uma
# caixa retangular em volta de uma cidade de contorno irregular inevitavelmente
# "vaza" pra cidades vizinhas que ficam na mesma faixa de latitude/longitude —
# confirmado na prática: essa caixa incluía Cubatão, Santos, São Vicente e
# Embu-Guaçu, todas fora do município de São Paulo mas dentro do retângulo, o que
# deixava passar rua de mesmo nome geocodificada na cidade errada. Não dá pra
# resolver isso só apertando os limites do retângulo sem também cortar bairros
# legítimos do extremo sul de SP (Parelheiros/Marsilac), então o retângulo fica
# só como filtro rápido e a validação de verdade é pelo nome do município mesmo.
SP_BOUNDS = {"lat_min": -24.01, "lat_max": -23.35, "lng_min": -46.83, "lng_max": -46.36}

def _dentro_de_sp(lat: float, lng: float) -> bool:
    """Triagem grosseira por coordenada — não substitui _e_municipio_sao_paulo."""
    return (SP_BOUNDS["lat_min"] <= lat <= SP_BOUNDS["lat_max"] and
            SP_BOUNDS["lng_min"] <= lng <= SP_BOUNDS["lng_max"])


def _normalizar(txt: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode().strip().lower()


def _e_municipio_sao_paulo(cidade: str) -> bool:
    """Compara o nome do município retornado pela fonte com 'São Paulo', ignorando
    acentuação/maiúsculas — é a validação que realmente impede um resultado de
    Cubatão/Santos/Embu-Guaçu (ou qualquer outra cidade) de ser aceito."""
    return _normalizar(cidade) == "sao paulo"


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
            if lat and lng and _e_municipio_sao_paulo(d.get("city", "")):
                lat, lng = float(lat), float(lng)
                if _dentro_de_sp(lat, lng):
                    return {"lat": lat, "lng": lng,
                            "bairro": d.get("neighborhood",""), "fonte": "brasilapi"}
    except Exception:
        logger.debug("Falha ao geocodificar CEP %s via BrasilAPI", cep, exc_info=True)
    return None


# Tipos de resultado do Nominatim aceitos como um endereço/local real (rua, quadra,
# bairro, prédio). Qualquer outra classe (amenity, shop, tourism, office, leisure...)
# é um ponto de interesse (ex.: "PUC-SP", "Centro Cultural BB") que pode aparecer no
# topo de uma busca por texto livre sem ter nenhuma relação com o CEP pesquisado —
# foi exatamente isso que causou pins errados no mapa (CEP da Vila Penteado/Zona Norte
# caindo em cima da PUC-SP em Perdizes). Só aceitamos tipos que descrevem geografia/
# endereçamento de fato.
_TIPOS_ENDERECO_VALIDOS = {
    "road", "residential", "house", "building", "postcode", "suburb",
    "neighbourhood", "quarter", "city_block", "place", "administrative",
}
_CLASSES_ENDERECO_VALIDAS = {"highway", "place", "boundary", "building", "landuse"}


def _resultado_e_endereco_valido(item: dict) -> bool:
    return (item.get("addresstype") in _TIPOS_ENDERECO_VALIDOS or
            item.get("class") in _CLASSES_ENDERECO_VALIDAS)


def _via_nominatim(cep: str, logradouro: str = "", bairro: str = "") -> dict | None:
    """
    Geocodifica via Nominatim usando busca ESTRUTURADA pelo nome da rua (campo
    `street`), não pelo número do CEP nem por texto livre. O Brasil tem cobertura
    muito ruim de CEPs no OpenStreetMap — uma busca por texto livre do tipo
    "02842-901 São Paulo SP" costuma cair em correspondência aproximada por
    relevância e retornar um ponto turístico/comercial qualquer dentro dos limites
    da cidade, sem nenhuma relação com o CEP. Sem um logradouro conhecido não há
    como fazer essa busca de forma confiável, então nesse caso desistimos (fica
    pendente) em vez de arriscar um pino errado.

    O `bairro` é recebido mas deliberadamente NÃO é enviado ao Nominatim (nem via
    `street`, nem via `county`): testado na prática, o nome oficial do bairro nos
    dados da prefeitura frequentemente não bate com o nome que o OSM usa pro mesmo
    lugar (ex.: CEP 02842-901 é "Vila Penteado" pro fisco e "Jardim Tiro ao Pombo"
    pra BrasilAPI) — incluir esse campo faz a busca estruturada zerar resultados
    em vez de refinar. O nome da rua sozinho já é específico o suficiente dentro
    do bounding box de São Paulo.
    """
    if not logradouro:
        return None
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "street": logradouro,
                "city": "São Paulo",
                "state": "São Paulo",
                "country": "Brazil",
                "format": "json",
                "limit": 5,
                "countrycodes": "br",
                "viewbox": "-47.0,-24.1,-46.3,-23.3",
                "bounded": 1,
                "addressdetails": 1,
            },
            headers=HEADERS, timeout=8
        )
        if r.status_code == 200:
            data = r.json()
            for item in data:
                if not _resultado_e_endereco_valido(item):
                    continue
                addr = item.get("address", {})
                cidade = addr.get("city") or addr.get("town") or addr.get("municipality") or ""
                if not _e_municipio_sao_paulo(cidade):
                    continue  # rua de mesmo nome em outra cidade (Cubatão, Santos, Embu-Guaçu...)
                lat = float(item["lat"])
                lng = float(item["lon"])
                if _dentro_de_sp(lat, lng):
                    return {"lat": lat, "lng": lng, "bairro": "", "fonte": "nominatim"}
    except Exception:
        logger.debug("Falha ao geocodificar CEP %s via Nominatim", cep, exc_info=True)
    return None


def geocodificar_um(cep: str, logradouro: str = "", bairro: str = "") -> dict | None:
    """Tenta BrasilAPI primeiro, depois Nominatim (busca estruturada por rua+bairro)."""
    geo = _via_brasilapi(cep)
    if not geo:
        time.sleep(1.1)  # respeita o limite de 1 req/s da política de uso do Nominatim
        geo = _via_nominatim(cep, logradouro, bairro)
    return geo


# ──────────────────────────────────────────────
# CACHE — leitura e escrita
# ──────────────────────────────────────────────

def _cep_limpo(cep: str) -> str:
    return cep.replace("-","").replace(".","").strip().zfill(8)


def _ler_cache(conn, cep: str) -> dict | None:
    row = conn.execute(
        "SELECT lat, lng, bairro, ok FROM geo_cache WHERE cep = ?", (cep,)
    ).fetchone()
    if not row:
        return None
    if row[3] == 0:
        return {"erro": True}
    if row[0] is None:
        return None
    return {"lat": row[0], "lng": row[1], "bairro": row[2] or ""}


def _salvar_cache(cep: str, geo: dict | None):
    conn = sqlite3.connect(DB_PATH)
    if geo:
        conn.execute(
            "INSERT OR REPLACE INTO geo_cache (cep, lat, lng, bairro, ok, fonte) VALUES (?,?,?,?,1,?)",
            (cep, geo["lat"], geo["lng"], geo.get("bairro",""), geo.get("fonte",""))
        )
    else:
        conn.execute(
            "INSERT OR REPLACE INTO geo_cache (cep, lat, lng, bairro, ok) VALUES (?,NULL,NULL,'',0)",
            (cep,)
        )
    conn.commit()
    conn.close()


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

def pontos_mapa(filtros: dict, ids: list = None, max_ceps: int = 60000) -> dict:
    """
    Retorna pontos que JÁ estão geocodificados (cache).
    Dispara geocoding em background para os que faltam.
    """
    init_geo_cache()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    def _multi_like(col: str, value: str):
        """Suporte a múltiplos valores separados por vírgula (chips) -> OR no SQL."""
        vals = [v.strip() for v in value.split(",") if v.strip()]
        if not vals:
            return None, []
        clauses = [f"UPPER({col}) LIKE UPPER(?)" for _ in vals]
        return "(" + " OR ".join(clauses) + ")", [f"%{v}%" for v in vals]

    # Monta WHERE para a query de transações
    conds, params = [], []
    if ids:
        ph = ','.join('?' * len(ids))
        conds.append(f"t.id IN ({ph})")
        params.extend(ids)
    else:
        if filtros.get('logradouro'):
            cl, pr = _multi_like("t.logradouro", filtros['logradouro'])
            if cl: conds.append(cl); params.extend(pr)
        if filtros.get('bairro'):
            cl, pr = _multi_like("t.bairro", filtros['bairro'])
            if cl: conds.append(cl); params.extend(pr)
        if filtros.get('cep'):
            ceps = [v.strip().replace('-', '') for v in filtros['cep'].split(",") if v.strip()]
            if ceps:
                conds.append("(" + " OR ".join(["t.cep LIKE ?"] * len(ceps)) + ")")
                params.extend(f"{c}%" for c in ceps)
        if filtros.get('numero'):
            numeros = [v.strip() for v in filtros['numero'].split(",") if v.strip()]
            if numeros:
                conds.append("(" + " OR ".join(["t.numero = ?"] * len(numeros)) + ")")
                params.extend(numeros)
        if filtros.get('ano_min'):
            conds.append("t.ano_referencia >= ?")
            params.append(int(filtros['ano_min']))
        if filtros.get('ano_max'):
            conds.append("t.ano_referencia <= ?")
            params.append(int(filtros['ano_max']))
        if filtros.get('valor_min'):
            conds.append("t.valor_declarado >= ?")
            params.append(float(filtros['valor_min']))
        if filtros.get('valor_max'):
            conds.append("t.valor_declarado <= ?")
            params.append(float(filtros['valor_max']))

    base_where = ("AND " + " AND ".join(conds)) if conds else ""

    # Agrega por CEP + JOIN com geo_cache
    rows = conn.execute(f"""
        SELECT
            REPLACE(t.cep, '-', '') AS cep_clean,
            MAX(t.bairro) AS bairro_db,
            MAX(t.logradouro) AS logradouro_db,
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
        GROUP BY cep_clean
        ORDER BY total DESC
        LIMIT {max_ceps}
    """, params).fetchall()

    conn.close()

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
                "bairro":     r["bairro_db"] or r["bairro_geo"] or "",
                "logradouro": r["logradouro_db"] or "",
                "count":     r["total"],
                "avg_valor": round(r["avg_valor"] or 0),
                "max_valor": round(r["max_valor"] or 0),
                "sum_valor": round(r["sum_valor"] or 0),
            })
        elif r["ok"] is None:  # nunca tentou geocodificar
            sem_geo.append(cep)

    # Geocodificação é feita por processo standalone (geocode_all.py) na VM,
    # não mais disparada por acesso ao site — evita sobrecarregar visitas com requests externos.

    return {
        "pontos": pontos,
        "total_ceps": len(rows),
        "geocodificados": len(pontos),
        "pendentes": len(sem_geo),
        "geo_status": status_geocoding(),
    }
