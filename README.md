# Dashboard ITBI · São Paulo

Dashboard para consulta das transações imobiliárias com recolhimento de ITBI da Prefeitura de SP.
Dados de **2006 a 2026**, atualizados mensalmente direto da fonte oficial.

Produção atual: **VPS Hostinger** — `https://itbismart.com.br` (landing na raiz, dashboard em `/dashboard`, também acessível em `http://179.197.67.42:8000`)

> Deploy anterior (legado): Oracle Cloud VM · `https://itbisp.mooo.com`

---

## Estrutura do projeto

```
ITBISP/
├── backend/
│   ├── main.py             — API FastAPI + serve frontend estático
│   ├── scraper.py          — Baixa planilhas XLSX e salva no SQLite
│   ├── scraper_csv.py      — Scraper otimizado (XLSX→CSV) p/ VMs com pouca RAM
│   ├── exportar.py         — Exportação Excel/PDF
│   ├── geo.py              — Geocodificação (mapa, desativado)
│   ├── auth.py             — Autenticação JWT
│   ├── billing.py          — Integração Stripe
│   ├── requirements.txt
│   └── itbi.db             — Banco SQLite (gerado pelo scraper, não commitado)
└── frontend/
    └── index.html          — SPA single-file (vanilla JS + Chart.js)
```

---

## Como rodar localmente

### 1. Instalar dependências

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar `.env` (em `backend/.env`)

```
JWT_SECRET=uma_chave_secreta_longa
FRONTEND_URL=http://localhost:8000        # em produção: https://itbismart.com.br/dashboard

# Stripe (assinatura mensal) — opcional em dev; obrigatório p/ cobrar em produção
STRIPE_SECRET_KEY=sk_test_...             # em produção: sk_live_...
STRIPE_PRICE_ID=price_...                 # se vazio, billing.py cria um Price R$30/mês na 1ª cobrança
STRIPE_WEBHOOK_SECRET=whsec_...           # segredo do endpoint /api/webhook/stripe (ativa a assinatura após o pagamento)
```

> Sem login em `localhost` — o middleware faz bypass de auth/paywall para `127.0.0.1`.

### 3. Baixar os dados

```bash
# Recentes (2024-2026) — carga leve, padrão
python scraper_csv.py

# Forçar re-download + limpar cache CSV
python scraper_csv.py --forcar --limpar-csv

# Estender para anos antigos
python scraper_csv.py --anos 2020 2021 2022 2023 2024 2025 2026
```

### 4. Subir a API

```bash
uvicorn main:app --reload
# → http://localhost:8000   (sem login — bypass automático em localhost)
# → http://localhost:8000/docs   (Swagger)
```

---

## Produção (VPS Hostinger · Ubuntu 24.04)

**IP:** `179.197.67.42` · **Porta:** `8000` · **App:** `/root/ITBISP`

O app roda como serviço `systemd` (`itbi`), que sobe no boot e reinicia sozinho se cair.

### Deploy do zero

```bash
apt update && apt install -y python3 python3-venv git
cd /opt && git clone https://github.com/joaopmd16/ITBISP.git
cd ITBISP && python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
# criar backend/.env (ver seção acima)
cd backend && python scraper_csv.py --forcar
```

### Serviço systemd (`/etc/systemd/system/itbi.service`)

```ini
[Unit]
Description=Dashboard ITBI-SP
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/ITBISP/backend
ExecStart=/root/ITBISP/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Comandos úteis

```bash
systemctl status itbi        # ver estado
systemctl restart itbi       # reiniciar (após atualizar código)
journalctl -u itbi -f        # logs ao vivo

# atualizar código do GitHub e reiniciar
cd /root/ITBISP && git pull && systemctl restart itbi
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

Documentação interativa: `/docs`

---

## Autenticação e assinatura (Stripe)

- **Login/cadastro:** `frontend/login.html` (em produção `https://itbismart.com.br/dashboard/login.html`).
  - **Entrar:** e-mail + senha.
  - **Criar conta:** nome, sobrenome, telefone (com máscara BR), e-mail, senha + confirmação. Os campos extras
    ficam `disabled` no modo login para não travar a validação nativa; o backend valida e grava tudo.
- **Paywall:** o middleware `exigir_assinatura_ativa` (em `main.py`) protege as rotas `/api/` (exceto
  `/api/auth/` e `/api/webhook/`). Só passam usuários com `assinaturas.status` em **`active`, `trialing` ou `dev`**;
  os demais recebem **402** e são mandados ao checkout. O `login.html` espelha essa mesma lista (`ACESSO_LIBERADO`).
- **Conta admin (bypass):** `admin@itbismart.com.br` com `status = 'dev'` entra direto no dashboard, sem Stripe.
- **Cobrança:** assinatura mensal **R$ 30,00** via Stripe Checkout (`/api/billing/checkout`). Após o pagamento,
  o Stripe chama o webhook `POST /api/webhook/stripe` (eventos `checkout.session.completed`,
  `customer.subscription.updated/deleted`, `invoice.payment_failed`), que atualiza `assinaturas.status` para `active`.
  Configurar `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID` e `STRIPE_WEBHOOK_SECRET` no `.env` (ver seção de config).

---

## Fonte dos dados (Prefeitura SP)

O scraper decide a URL de cada ano pelo dicionário `ARQUIVOS` em `scraper_csv.py`.
Para o **ano atual** a URL é buscada dinamicamente na página oficial (o nome do arquivo
muda a cada atualização). Para os demais anos usa-se a URL fixa.

**Importante:** o **ano de cada registro é lido pelo nome da aba** (ex.: `JAN-2025`),
não pela "gaveta" do ano. Isso evita que um arquivo publicado fora de ordem (ex.: o
consolidado de 2025 publicado em jan/2026) seja gravado com o ano errado.

Total atual: **~539 mil transações** (2024–2026, com 2025 completo).

---

## Git

```
main          — versão atual (v2)
v1-stable     — tag do estado estável pré-v2 (commit ac4ce66)
```
