# Dashboard ITBI · São Paulo

Dashboard para consulta das transações imobiliárias com recolhimento de ITBI da Prefeitura de SP.
Dados de **2006 a 2026**, atualizados mensalmente direto da fonte oficial.

---

## Estrutura do projeto

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

## Rodar localmente (Windows)

```powershell
cd D:\itbi-dashboard\backend
python -m uvicorn main:app --reload
```

Acessa em: http://localhost:8000/app

---

## Servidor Oracle Cloud (produção)

**IP:** `137.131.160.254`  
**URL:** http://137.131.160.254:8000/app  
**Chave SSH:** `D:\itbi-dashboard\Oracle\ssh-key-2026-05-16.key`

### Conectar via SSH

```powershell
ssh -i "D:\itbi-dashboard\Oracle\ssh-key-2026-05-16.key" ubuntu@137.131.160.254
```

### Conectar via VS Code

Remote-SSH → `itbi-oracle` (já configurado em `~/.ssh/config`)

### Comandos do serviço (rodar na VM)

```bash
# Ver status
sudo systemctl status itbi

# Reiniciar após mudanças no backend
sudo systemctl restart itbi

# Ver logs em tempo real
sudo journalctl -u itbi -f

# Parar / iniciar
sudo systemctl stop itbi
sudo systemctl start itbi
```

### Subir arquivos do PC para a VM (PowerShell Admin)

```powershell
# Só o frontend (mais comum)
scp -i "D:\itbi-dashboard\Oracle\ssh-key-2026-05-16.key" "D:\itbi-dashboard\frontend\index.html" ubuntu@137.131.160.254:~/frontend/

# Só o scraper (quando alterar regras de importação)
scp -i "D:\itbi-dashboard\Oracle\ssh-key-2026-05-16.key" "D:\itbi-dashboard\backend\scraper.py" ubuntu@137.131.160.254:~/backend/

# Backend inteiro
scp -i "D:\itbi-dashboard\Oracle\ssh-key-2026-05-16.key" -r "D:\itbi-dashboard\backend" ubuntu@137.131.160.254:~/

# Tudo
scp -i "D:\itbi-dashboard\Oracle\ssh-key-2026-05-16.key" -r "D:\itbi-dashboard\backend" "D:\itbi-dashboard\frontend" ubuntu@137.131.160.254:~/
```

---

## Atualização dos dados (scraper)

```bash
# Rodar na VM — baixa só o ano atual
cd ~/backend
python3 scraper.py --anos 2026

# Todos os anos (demora 10-20 min)
python3 scraper.py
```

Ou via API: `POST /api/sincronizar`

---

## API REST

```
GET  /api/transacoes?logradouro=paulista&ano_min=2020
GET  /api/resumo?bairro=pinheiros
GET  /api/autocomplete/logradouro?q=august
GET  /api/autocomplete/bairro?q=pin
GET  /api/status
GET  /api/mapa
GET  /api/exportar/excel
GET  /api/exportar/pdf
POST /api/sincronizar
```

Documentação interativa: http://137.131.160.254:8000/docs

---

## Banco de dados

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
    sql_terreno         TEXT,
    area_terreno        REAL,
    area_construida     REAL,
    valor_declarado     REAL,
    valor_financiado    REAL,
    valor_itbi          REAL,
    natureza_transacao  TEXT,
    tipo_uso            TEXT
);
```
