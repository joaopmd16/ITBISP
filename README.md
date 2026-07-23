# Dashboard ITBI · São Paulo

Dashboard para consulta das transações imobiliárias com recolhimento de ITBI da Prefeitura de SP.
Dados de **2006 a 2026**, atualizados direto da fonte oficial — pelo painel admin ou por scraper manual.

Produção atual: **VPS Hostinger** — `https://itbismart.com.br` (landing na raiz, dashboard em `/dashboard`, também acessível em `http://179.197.67.42:8000`)

> Deploy anterior (legado): Oracle Cloud VM · `https://itbisp.mooo.com`

---

## Estrutura do projeto

```
ITBISP/
├── backend/
│   ├── main.py             — API FastAPI + serve frontend estático
│   ├── scraper.py          — Scraper original (openpyxl, linha a linha)
│   ├── scraper_csv.py      — Scraper otimizado (XLSX→CSV) p/ VMs com pouca RAM
│   ├── geocode_all.py      — Geocodificação em lote de todos os CEPs (rodar manualmente na VPS)
│   ├── exportar.py         — Exportação Excel/PDF
│   ├── geo.py              — Geocodificação do mapa (cache-only, sem chamadas externas em runtime)
│   ├── auth.py             — Autenticação JWT
│   ├── billing.py          — Integração Stripe (assinatura + cupons)
│   ├── emailing.py         — E-mails transacionais via Resend
│   ├── requirements.txt
│   ├── itbi.db             — Banco SQLite (gerado pelo scraper, não commitado)
│   └── uploads/             — Anexos de tickets de suporte (gerado em runtime, não commitado)
├── frontend/
│   ├── index.html          — SPA single-file (vanilla JS + Chart.js + Leaflet) — dashboard principal
│   ├── admin.html           — Painel admin single-file (usuários, cupons, sincronização, tickets)
│   └── login.html          — Login/cadastro/redefinição de senha
└── landing/
    └── Next.js — landing page de marketing, deploy como export estático na raiz do domínio
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
ADMIN_EMAIL=admin@itbismart.com.br        # e-mail com acesso ao painel /dashboard/admin.html

# Stripe (assinatura mensal) — opcional em dev; obrigatório p/ cobrar em produção
STRIPE_SECRET_KEY=sk_test_...             # em produção: sk_live_...
STRIPE_PRICE_ID=price_...                 # se vazio, billing.py cria um Price na 1ª cobrança
STRIPE_WEBHOOK_SECRET=whsec_...           # segredo do endpoint /api/webhook/stripe

# E-mails transacionais (verificação de conta, redefinição de senha, tickets de suporte)
RESEND_API_KEY=re_...
RESEND_FROM=ITBI Smart <noreply@itbismart.com.br>
```

> Sem login em `localhost` — o middleware faz bypass de auth/paywall para `127.0.0.1`.

### 3. Baixar os dados

```bash
# Recentes (2024-2026) — carga leve, padrão
python scraper_csv.py

# Forçar re-download + limpar cache CSV
python scraper_csv.py --forcar --limpar-csv

# Estender para anos antigos
python scraper_csv.py --anos 2006 2010 2015 2020 2021 2022 2023 2024 2025 2026
```

### 4. Subir a API

```bash
uvicorn main:app --reload
# → http://localhost:8000          (sem login — bypass automático em localhost)
# → http://localhost:8000/docs     (Swagger)
# → http://localhost:8000/dashboard/admin.html   (painel admin)
```

---

## Produção (VPS Hostinger · Ubuntu 24.04)

**IP:** `179.197.67.42` · **Porta:** `8000` · **App:** `/root/ITBISP`

O app roda como serviço `systemd` (`itbi`), que sobe no boot e reinicia sozinho se cair.
Nginx faz o reverse proxy + TLS (Certbot) na frente — `/etc/nginx/sites-available/itbismart`.

### Deploy do zero

```bash
apt update && apt install -y python3 python3-venv git nginx
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

### Nginx — pontos de atenção

Os blocos `location /api/` e `location /dashboard` no site do nginx precisam de:

```nginx
client_max_body_size 20M;          # default do nginx é 1MB — quebra upload de anexo/foto
proxy_http_version 1.1;
proxy_set_header Connection "";    # default HTTP/1.0 pode truncar respostas maiores
```

### Comandos úteis

```bash
systemctl status itbi        # ver estado
systemctl restart itbi       # reiniciar (após atualizar código Python)
journalctl -u itbi -f        # logs ao vivo

# atualizar código do GitHub e reiniciar
cd /root/ITBISP && git pull && pip install -r backend/requirements.txt && systemctl restart itbi
# (o pip install só é necessário quando requirements.txt muda; mudanças só em frontend/*.html
#  não precisam nem de restart, StaticFiles serve direto do disco)
```

---

## API REST

```
GET  /api/transacoes?logradouro=paulista&ano_min=2020&ano_max=2026
GET  /api/resumo?bairro=pinheiros
GET  /api/autocomplete/{logradouro,bairro,cep,sql,numero}?q=...
GET  /api/iptu/{sql_terreno}
GET  /api/status
GET  /api/exportar/{excel,pdf}
GET  /api/mapa                              # pontos geocodificados por CEP (cache-only)
GET  /api/mapa/status
POST /api/sincronizar                       # trigger legado (SYNC_SECRET), usado por script/cron externo

# Autoatendimento do usuário (perfil, senha, e-mail)
GET/PUT  /api/usuario/perfil
POST     /api/usuario/trocar-email
POST     /api/usuario/trocar-senha
GET      /api/auth/confirmar-troca-email

# Tickets de suporte (chat)
GET/POST /api/tickets
GET/POST /api/tickets/{id}/mensagens
POST     /api/tickets/{id}/encerrar
GET      /api/tickets/anexos/{ticket_id}/{arquivo}

# Painel admin (exigir_admin — só ADMIN_EMAIL)
GET/POST /api/admin/usuarios
PUT      /api/admin/usuarios/{id}/perfil
POST     /api/admin/usuarios/{id}/{desativar,reativar}
DELETE   /api/admin/usuarios/{id}
GET/POST /api/admin/cupons
POST     /api/admin/sincronizar
GET/POST /api/admin/tickets*
```

Documentação interativa: `/docs`

---

## Autenticação e assinatura (Stripe)

- **Login/cadastro:** `frontend/login.html` (em produção `https://itbismart.com.br/dashboard/login.html`).
  - **Entrar:** e-mail + senha.
  - **Criar conta:** nome, sobrenome, telefone (com máscara BR), e-mail, senha + confirmação.
- **Paywall:** o middleware `exigir_assinatura_ativa` (em `main.py`) protege as rotas `/api/` (exceto
  `/api/auth/`, `/api/webhook/`, `/api/tickets/anexos/` e `/api/billing/checkout`/`/api/tickets`, que só
  exigem login, não assinatura ativa). Só passam usuários com `assinaturas.status` em **`active`,
  `trialing` ou `dev`**; os demais recebem **402** e são mandados ao checkout.
- **Conta admin (bypass):** e-mail definido em `ADMIN_EMAIL` com `status = 'dev'` entra direto no
  dashboard, sem Stripe, e tem acesso ao painel `/dashboard/admin.html`.
- **Cobrança:** assinatura mensal (preço configurado em `STRIPE_PRICE_ID`) via Stripe Checkout
  (`/api/billing/checkout`). Após o pagamento, o Stripe chama o webhook `POST /api/webhook/stripe`
  (eventos `checkout.session.completed`, `customer.subscription.updated/deleted`,
  `invoice.payment_failed`), que atualiza `assinaturas.status` para `active`.
- **Cupons de desconto:** geridos direto pelo painel admin (`/dashboard/admin.html` → aba Cupons),
  sem precisar abrir o Dashboard da Stripe manualmente.

---

## Painel admin (`/dashboard/admin.html`)

Restrito a `ADMIN_EMAIL`. Três abas:

- **Usuários** — listar/criar/editar, liberar/revogar/desativar/reativar acesso, resetar senha,
  ver pagamentos, excluir permanentemente (com confirmação forte).
- **Cupons** — criar/listar/desativar cupons de desconto da Stripe.
- **Atualizar dados** — dispara o scraper e acompanha o log em tempo real, sem precisar de SSH.
- **Tickets** — responde aos chamados de suporte abertos pelos usuários (texto, anexo, áudio, print).

## Suporte (chat de tickets)

Bolinha flutuante no dashboard principal abre um chat de suporte com histórico de vários tickets.
Ambos os lados (usuário e admin) podem anexar arquivo, gravar áudio e capturar a própria tela, e
encerrar um ticket (fica somente leitura depois). Sem WebSocket — atualiza por polling.

---

## Fonte dos dados (Prefeitura SP)

O scraper decide a URL de cada ano pelo dicionário `ARQUIVOS` em `scraper_csv.py`.
Para o **ano atual** a URL é buscada dinamicamente na página oficial (o nome do arquivo
muda a cada atualização). Para os demais anos usa-se a URL fixa.

**Importante:** o **ano de cada registro é lido pelo nome da aba** (ex.: `JAN-2025`),
não pela "gaveta" do ano. Isso evita que um arquivo publicado fora de ordem (ex.: o
consolidado de 2025 publicado em jan/2026) seja gravado com o ano errado.

Total atual: **~2,59 milhões de transações**, histórico completo 2006–2026 (confirmar via `/api/status`).

---

## Git

```
main          — versão atual (v2)
v1-stable     — tag do estado estável pré-v2 (commit ac4ce66)
```
