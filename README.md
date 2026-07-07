# Dashboard ITBI · São Paulo

Dashboard para consulta das transações imobiliárias com recolhimento de ITBI da Prefeitura de SP.
Dados de **2006 a 2026**, atualizados mensalmente direto da fonte oficial.

Produção: **https://itbisp.mooo.com**

---

## Estrutura do projeto

```
itbi-dashboard/
├── backend/
│   ├── main.py             — API FastAPI + serve frontend estático
│   ├── scraper.py          — Baixa planilhas XLSX e salva no SQLite
│   ├── scraper_csv.py      — Variante CSV do scraper
│   ├── exportar.py         — Exportação Excel/PDF
│   ├── geo.py              — Geocodificação (mapa, desativado)
│   ├── auth.py             — Autenticação JWT
│   ├── billing.py          — Integração Stripe
│   ├── requirements.txt
│   └── itbi.db             — Banco SQLite (gerado pelo scraper, não commitado)
├── frontend/
│   └── index.html          — SPA single-file (vanilla JS + Chart.js)
├── deploy-v2.ps1           — Deploy para VM (scp + restart)
├── rollback-v1.ps1         — Rollback para v1-stable na VM
└── backup-v1/              — Snapshot dos arquivos antes do deploy v2
```

---

## Como rodar localmente (Windows)

### 1. Instalar dependências

```powershell
cd D:\itbi-dashboard\backend
pip install -r requirements.txt
```

### 2. Criar flag de dev local (desativa tarefas pesadas em background)

```powershell
New-Item backend\.dev_local -ItemType File
```

### 3. Baixar os dados

```powershell
# Recentes apenas (rápido, para testar)
python scraper.py --anos 2024 2025 2026

# Todos os anos (10-20 min)
python scraper.py
```

### 4. Subir a API

```powershell
python -m uvicorn main:app --reload
# → http://localhost:8000  (sem login — bypass automático em localhost)
```

---

## Produção (Oracle Cloud VM)

**IP:** `137.131.160.254`  
**Domínio:** `https://itbisp.mooo.com`  
**Chave SSH:** `C:\Users\gel\.ssh\itbi.key`

### Deploy

```powershell
# Deploy completo v2
.\deploy-v2.ps1

# Rollback para v1 se der problema
.\rollback-v1.ps1
```

### Manual (SSH)

```powershell
$KEY = "C:/Users/gel/.ssh/itbi.key"
$VM  = "ubuntu@137.131.160.254"

# Conectar
ssh -i $KEY $VM

# Enviar arquivos
scp -i $KEY backend\main.py    "${VM}:~/backend/main.py"
scp -i $KEY frontend\index.html "${VM}:~/frontend/index.html"

# Reiniciar serviço
ssh -i $KEY $VM "sudo systemctl restart itbi"
```

### Comandos na VM

```bash
sudo systemctl restart itbi
sudo systemctl status itbi
sudo journalctl -u itbi -f
```

---

## API REST

```
GET  /api/transacoes?logradouro=paulista&ano_min=2020&ano_max=2026
GET  /api/resumo?bairro=pinheiros
GET  /api/autocomplete/logradouro?q=august&offset=0
GET  /api/autocomplete/bairro?q=pin
GET  /api/autocomplete/cep?q=01310
GET  /api/autocomplete/sql?q=3520
GET  /api/iptu/{sql_terreno}
GET  /api/status
GET  /api/exportar/excel
GET  /api/exportar/pdf
POST /api/sincronizar
```

Documentação interativa: `https://itbisp.mooo.com/docs`

---

## Git

```
main          — versão atual (v2)
v1-stable     — tag apontando para o estado estável pré-v2 (commit ac4ce66)
```

Para fazer rollback de código:
```powershell
git checkout v1-stable
```
