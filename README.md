# 🏠 Dashboard ITBI · São Paulo

Dashboard para consulta das transações imobiliárias com recolhimento de ITBI da Prefeitura de SP.
Dados de **2006 a 2026**, atualizados mensalmente direto da fonte oficial.

---

## 📁 Estrutura do projeto

```
itbi-dashboard/
├── backend/
│   ├── main.py             ← API FastAPI
│   ├── scraper.py          ← Baixa planilhas e salva no banco
│   ├── exportar.py         ← Exportação Excel/PDF
│   ├── geo.py              ← Geocodificação para o mapa
│   ├── requirements.txt
│   └── itbi.db             ← Banco SQLite (gerado automaticamente)
└── frontend/
    └── index.html          ← Dashboard (interface)
```

---

## 🚀 Como rodar localmente (Windows)

### 1. Instalar dependências

```powershell
cd D:\itbi-dashboard\backend
pip install -r requirements.txt
```

### 2. Baixar os dados (primeira vez)

```powershell
# Todos os anos (10-20 min)
python scraper.py

# Ou só os recentes para testar rápido
python scraper.py --anos 2024 2025 2026
```

### 3. Subir a API

```powershell
python -m uvicorn main:app --reload
```

Acessa em: http://localhost:8000

---

## ☁️ Servidor Oracle Cloud (produção)

**IP:** `137.131.160.254`
**URL:** http://137.131.160.254

**Chave SSH:** `D:\itbi-dashboard\Oracle\ssh-key-2026-05-16.key`

### Conectar via SSH

```powershell
ssh -i "$env:USERPROFILE\.ssh\itbi-oracle.key" ubuntu@137.131.160.254
```

### Subir arquivos para a VM

```powershell
# Frontend
scp -i "$env:USERPROFILE\.ssh\itbi-oracle.key" "D:\itbi-dashboard\frontend\index.html" ubuntu@137.131.160.254:~/frontend/

# Backend
scp -i "$env:USERPROFILE\.ssh\itbi-oracle.key" "D:\itbi-dashboard\backend\main.py" ubuntu@137.131.160.254:~/backend/

# Banco (após rodar scraper localmente)
scp -i "$env:USERPROFILE\.ssh\itbi-oracle.key" "D:\itbi-dashboard\backend\itbi.db" ubuntu@137.131.160.254:~/backend/
```

### Comandos do serviço (na VM)

```bash
sudo systemctl restart itbi
sudo systemctl status itbi
sudo journalctl -u itbi -f
```

---

## 🔄 Atualização dos dados

```bash
# Na VM ou PC — baixa só o ano atual
python3 scraper.py --anos 2026

# Todos os anos (rodar no PC, não na VM — pouca RAM)
python scraper.py --forcar
```

Ou via API: `POST /api/sincronizar`

---

## 📡 API REST

```
GET  /api/transacoes?logradouro=paulista&ano_min=2020
GET  /api/resumo?bairro=pinheiros
GET  /api/autocomplete/logradouro?q=august
GET  /api/autocomplete/bairro?q=pin
GET  /api/status
GET  /api/exportar/excel
GET  /api/exportar/pdf
POST /api/sincronizar
```

Documentação interativa: http://137.131.160.254/docs

---

## 🗄️ Banco de dados

```sql
CREATE TABLE transacoes (
    id                  INTEGER PRIMARY KEY,
    ano_referencia      INTEGER,
    mes_referencia      INTEGER,
    data_transacao      TEXT,
    logradouro          TEXT,
    numero              TEXT,
    complemento         TEXT,
    bairro              TEXT,
    cep                 TEXT,
    sql_terreno         TEXT,      -- N° IPTU (código do imóvel)
    area_terreno        REAL,
    area_construida     REAL,
    valor_declarado     REAL,
    valor_financiado    REAL,
    valor_itbi          REAL,
    natureza_transacao  TEXT,
    tipo_uso            TEXT
);
```
