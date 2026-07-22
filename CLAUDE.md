# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dashboard for querying ITBI (real estate transfer tax) transactions in São Paulo, 2006–2026. Data is scraped from the official Prefeitura SP source, stored in SQLite, and served via a FastAPI backend with a single-file SPA frontend.

**Current production:** Hostinger VPS (Ubuntu 24.04, 4 GB) — `https://itbismart.com.br` (also reachable at `http://179.197.67.42:8000`), app at `/root/ITBISP`, running as the `itbi` systemd service.

**Legacy production:** Oracle Cloud VM — `https://itbisp.mooo.com` (`ubuntu@137.131.160.254`).

### Domain & HTTPS

- Domain `itbismart.com.br` is registered at registro.br, but DNS is managed via **Cloudflare** (nameservers `bristol.ns.cloudflare.com` / `felipe.ns.cloudflare.com`) because registro.br's own DNS panel (using their default nameservers) has no zone editor in this account — only a nameserver-swap screen.
- A record in Cloudflare points to `179.197.67.42`, set to **DNS only** (grey cloud, not proxied) — Cloudflare is DNS-host only here, not a proxy/CDN. SSL/TLS termination happens directly on the VPS.
- HTTPS on the VPS is handled by **Nginx** (reverse proxy, `/etc/nginx/sites-available/itbismart`) + **Certbot/Let's Encrypt** (auto-renewing cert).
- Root domain, `www`, and HTTP→HTTPS redirect are all confirmed working.

### URL structure (root = landing page, /dashboard = app)

- `itbismart.com.br` (root) serves the **static-exported Next.js landing page** directly via Nginx `root /var/www/itbismart-landing;` (`try_files $uri $uri.html $uri/ =404`) — not proxied to FastAPI. Static files are built locally (`next build`, `output: "export"` in `landing/next.config.ts`, since the VM has no Node.js runtime) and uploaded via SFTP.
- `itbismart.com.br/dashboard` and `itbismart.com.br/api/` are `proxy_pass`'d to FastAPI on `127.0.0.1:8000`. In `backend/main.py`, the frontend `StaticFiles` mount is at `/dashboard` (not `/`), so all frontend asset paths, login/logout redirects, and post-checkout redirects in `frontend/index.html`/`frontend/login.html` use `/dashboard/...` prefixes.
- `backend/.env`'s `FRONTEND_URL` on the VM is `https://itbismart.com.br/dashboard` (drives Stripe `success_url`/`cancel_url`/`return_url` in `backend/billing.py`).
- Landing page CTAs (`Navbar.tsx`, `Hero.tsx`, `Pricing.tsx`, `Footer.tsx`) link to `/dashboard`.
- Static landing files live at `/var/www/itbismart-landing` on the VM (not under `/root/...` — `/root` is `700` and blocks the `www-data` Nginx worker from traversing into anything beneath it, even if the target dir itself is world-readable).
- `frontend/login.html` is styled to match the **dashboard** design tokens: dark theme (`--bg:#000`, `--surface:#0d0d0d`), primary `#e08560`, rounded card (`20px`) + inputs (`16px`) + pill buttons, a segmented "Entrar / Criar conta" toggle, plus the landing-page `.bg-grid` + two animated glow blobs (CSS-only). Plus Jakarta Sans font.

### Authentication & billing (Stripe)

- **Login/signup UI** (`frontend/login.html`): the "Entrar" tab is e-mail + senha; the "Criar conta" tab additionally collects **nome, sobrenome, telefone** (BR phone mask via `mascaraTelefone`) and a **password confirmation** (validated client-side). The extra fields live in `.only-cadastro` blocks and are toggled `disabled`/`required` per mode so native validation doesn't trip on hidden required fields.
- **`usuarios` table** has `nome`, `sobrenome`, `telefone` columns added by an idempotent `ALTER TABLE ... ADD COLUMN` migration at `main.py` startup (SQLite has no `ADD COLUMN IF NOT EXISTS`; wrapped in try/except). `/api/auth/registrar` uses the `CadastroIn` model and validates/stores them; `/api/auth/login` still uses `CredenciaisIn` (e-mail + senha).
- **Paywall:** the `exigir_assinatura_ativa` middleware (`main.py`) treats `assinaturas.status` in **`active`, `trialing`, `dev`** as allowed; others get **402**. `login.html`'s `ACESSO_LIBERADO = ['active','trialing','dev']` must mirror this list — a mismatch is what sent the `dev` admin to a broken Stripe checkout before it was fixed.
- **Admin bypass:** `admin@itbismart.com.br` (password known to the user, not stored in repo or Claude's memory) has `status = 'dev'` → enters the dashboard directly, no Stripe.
- **Stripe is LIVE in production.** `backend/.env` on the VM holds a real `sk_live_` `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`, and `STRIPE_WEBHOOK_SECRET`. `billing.py`'s `garantir_price_id()` fallback creates a price only if `STRIPE_PRICE_ID` is empty. A webhook endpoint `https://itbismart.com.br/api/webhook/stripe` is registered (status `enabled`) with events `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`; `checkout.session.completed` flips the user's `assinaturas.status` to `active`. **Secrets (`sk_live`, `whsec_`) are never pasted by Claude** — the user sets them directly on the VM; Claude only reads/creates non-secret resources (price id, coupon id, promotion code, endpoint listing) via scripts that read the key from `.env` without printing it.
- **Current pricing (as of the ITBIREMAX30 promo):** base price is **R$ 49,90/month** (`STRIPE_PRICE_ID` in `.env` points to this Price; the original R$ 30 Price was deactivated via `stripe.Price.modify(id, active=False)` — kept around, just not used for new checkouts). Subscribers who were already on the old R$ 30 Price are unaffected (Stripe subscriptions stay pinned to whatever Price they were created with; changing the "current" `STRIPE_PRICE_ID` only affects *new* checkouts).
- **Promo coupon `ITBIREMAX30`:** currently a Stripe Coupon (`amount_off=2000`, `currency=brl`, `duration=repeating`, `duration_in_months=3`) discounts the R$49,90 base down to **R$29,90** for the customer's first 3 billing cycles, then it reverts automatically to R$49,90 — no manual intervention needed, this is native Stripe coupon behavior. (The original coupon, `qVqcIJu5`/`amount_off=1990`→R$30,00, was deactivated and replaced this session; since Stripe coupons are immutable, "editing" the promo always means deactivating the old `PromotionCode` and creating a new Coupon+PromotionCode reusing the same human-readable code — `billing.py`'s `criar_cupom()`/`listar_cupons()`/`desativar_promo_code()` wrap this, and the admin panel's Cupons tab does it through the UI now instead of a one-off script.) The `PromotionCode` (code `ITBIREMAX30`) has `expires_at` set to 2026-08-12 23:59:59 `America/Sao_Paulo`; after that date the code can no longer be *redeemed* on a new checkout, but anyone who redeemed it before the deadline keeps their 3-month discount window uninterrupted. `billing.py`'s `criar_checkout_session()` passes `allow_promotion_codes=True` so the Stripe-hosted checkout page shows a coupon input field. The landing page (`landing/components/Pricing.tsx`) displays the promo (struck-through R$49,90 → R$29,90, with the coupon code and expiry date) as static marketing copy — it does not call the Stripe API, so if the promo terms change again both `Pricing.tsx` and the Stripe-side Coupon/PromotionCode (now doable from the admin panel) need to be updated together.
- **Subscription renewal date (`assinaturas.periodo_fim`)**: an `INTEGER` (Unix timestamp) column populated from Stripe webhook events (`checkout.session.completed` fetches it via `billing.detalhes_assinatura()`; `customer.subscription.updated`/`.deleted` read `current_period_end` directly off the event payload). `admin_listar_usuarios()` (`main.py`) does a one-time lazy backfill for any `active`/`past_due`/`unpaid` subscription missing this value (subscriptions created before the column existed), so it self-heals without a migration script.

### Admin panel (`frontend/admin.html`)

Single-file SPA (same hand-written HTML/JS style as `index.html`, no build step), served at `/dashboard/admin.html`, gated by `exigir_admin` (`main.py`) — 403 for any JWT whose e-mail isn't `ADMIN_EMAIL`. Three top-level sections (client-side nav, no new routes):
- **Usuários** — table of all users with 5 client-side status sub-tabs (Todos/Pagantes/Trial ou Liberado/Sem acesso/Desativados) filtering the already-fetched array, no extra API calls per tab. Row/detail actions: Liberar, Revogar, Resetar senha, Pagamentos, **Desativar/Reativar** (soft-delete, reversible — see below), **Excluir** (hard delete, irreversible — see below), and an inline "Editar dados" form (nome/sobrenome/telefone/e-mail) hitting `PUT /api/admin/usuarios/{id}/perfil` directly, no confirmation flow (admin override, for support cases).
- **Cupons** — create/list/deactivate Stripe promo codes through `billing.criar_cupom()`/`listar_cupons()`/`desativar_promo_code()` (see "Promo coupon" above) instead of one-off scripts.
- **Atualizar dados** — triggers the scraper via `POST /api/admin/sincronizar` (JWT-gated) and polls `GET /api/sincronizar/status` every 3s for a live log while `rodando=true`. This reuses the exact same background-task core (`_disparar_sincronizacao()`) as the legacy `POST /api/sincronizar?senha=<SYNC_SECRET>` endpoint used by external cron — refactored out of a single function so both callers share one implementation instead of duplicating the scraper-trigger logic.
  - **`atualizarStatusSync()` must use the authenticated `api()` helper, not a bare `fetch`** — `/api/sincronizar/status` sits behind `exigir_assinatura_ativa` (`main.py`) for any request not originating from `127.0.0.1`, so an unauthenticated browser fetch gets a silent 401 and the log box just stays empty forever. This bit once already; if the sync log appears blank again, check this first before assuming the backend is broken.

**Soft-delete (`usuarios.ativo`, default 1):** `POST /api/admin/usuarios/{id}/desativar` sets `ativo=0`, force-cancels any Stripe subscription, and sets `assinaturas.status='inativa'`. Login (`/api/auth/login`) rejects `ativo=0` with 403, **and** the `exigir_assinatura_ativa` middleware also checks `ativo` on every protected request — both checks are needed because a JWT is stateless and stays valid for `JWT_EXP_DIAS=7` days regardless of DB state, so blocking only at login wouldn't cut off an already-logged-in session immediately (confirmed requirement: deactivation must be instant, not "on next login"). `POST /api/admin/usuarios/{id}/reativar` reverses it (`ativo=1` only — does not restore the old assinatura status).

**Hard delete:** `DELETE /api/admin/usuarios/{id}` permanently removes the user and all related rows (`assinaturas`, `senhas_antigas`, `admin_logs`) — no soft-delete, no recovery. The admin.html confirmation modal requires typing the user's exact e-mail before the delete button enables (a plain `confirm()` was judged too weak for a truly irreversible action). Distinct from "Desativar" — always clarify which one a request means, they are not synonyms in this codebase.

**SQLite `busy_timeout`:** `get_db()` (`main.py`) sets `PRAGMA busy_timeout = 10000` on every connection. Without it, any admin write (e.g. `desativar`) racing against the scraper/`popular_iptu()` (which holds long write transactions during a sync) fails immediately with `sqlite3.OperationalError: database is locked` instead of queueing — this actually happened in production once a sync + an admin action overlapped, hence the fix.

### User self-service profile (`frontend/index.html` "Minha conta")

The "Minha conta" panel (topbar icon, `toggleConta()`) is a **centered modal** (`.acc-modal`/`.acc-backdrop`, 2-column grid ≥760px), not the side `.settings-panel` used by the gear/"Configurações" icon next to it — it outgrew the side-panel width, so don't copy that pattern back if extending this panel further.

- **Edit nome/sobrenome/telefone** — `PUT /api/usuario/perfil`, applies immediately, no confirmation.
- **Change e-mail** — `POST /api/usuario/trocar-email` does NOT change `usuarios.email` directly; it stores the new address in `usuarios.email_pendente` and reuses the signup-verification columns (`token_verificacao`/`token_verificacao_exp`) to send a confirmation link (`emailing.enviar_confirmacao_troca_email`) to the **new** address. Only `GET /api/auth/confirmar-troca-email?token=...` (public route, no session needed — it's opened from an e-mail client) actually swaps `email ← email_pendente`. Reusing the verification-token columns is safe because login already requires `email_verificado=1`, so by the time a user reaches this panel their signup verification flow has already cleared those columns — no state collision. The admin panel shows `email_pendente` on a user's detail view when a swap is awaiting confirmation.
- **Change password** — `POST /api/usuario/trocar-senha` requires the current password (verified via `auth.verificar_senha`) plus the new one; reuses `_trocar_senha()`/`_senha_ja_usada()` (`main.py`), the same helpers the admin "Resetar senha" and "Esqueci minha senha" flows use, so password-history/reuse rules stay consistent across all three paths.

### VPS access

SSH key auth is not set up for this VPS (a key existed locally but was for a different, unrelated server) — access is by **root password only**. Windows Git Bash has no `sshpass`/`plink`/`expect`, so remote commands are run via a small `paramiko`-based Python script (see scratchpad `ssh_run.py` pattern in past sessions, easily recreated):

```python
import sys, paramiko, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("179.197.67.42", username="root", password=os.environ["VPS_PASS"], timeout=15)
stdin, stdout, stderr = client.exec_command(sys.argv[1], get_pty=True, timeout=120)
print(stdout.read().decode(errors="replace"))
print("EXIT:", stdout.channel.recv_exit_status())
```

Standard deploy after a push: `cd /root/ITBISP && git pull && systemctl restart itbi && sleep 3 && systemctl is-active itbi`.

**Every push to `main` and every production deploy requires explicit user confirmation** (AskUserQuestion) — the auto-mode classifier blocks unconfirmed pushes to the default branch. Ask before each one, don't batch/assume approval carries over.

## Commands

### Local development

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# .env is required (backend/.env): JWT_SECRET, STRIPE_SECRET_KEY (optional), FRONTEND_URL

# Populate database (recent years 2024-2026 is the default)
python scraper_csv.py
python scraper_csv.py --forcar --limpar-csv          # force re-download + clear CSV cache
python scraper_csv.py --anos 2020 2021 2022 2023 2024 2025 2026   # extend to older years

# Start API (no login on localhost — auth bypass by client host)
uvicorn main:app --reload      # → http://localhost:8000  ·  /docs for Swagger
```

### Production (Hostinger VPS — 179.197.67.42)

```bash
# App is a systemd service
systemctl status itbi
systemctl restart itbi         # after code changes
journalctl -u itbi -f          # live logs

# Update from GitHub and restart
cd /root/ITBISP && git pull && systemctl restart itbi
```

The `itbi.service` unit runs `uvicorn main:app --host 0.0.0.0 --port 8000` from `/root/ITBISP/backend` with `Restart=always` and is `enabled` (survives reboot). See README for the full unit file.

## Architecture

```
backend/
  main.py         — FastAPI app; serves API + mounts frontend as static files
  scraper.py      — Original scraper (openpyxl row-by-row)
  scraper_csv.py  — Optimized scraper: XLSX→CSV cache, one sheet at a time (low RAM)
  exportar.py     — Excel/PDF export helpers (called by main.py export routes)
  geo.py          — Geocoding (map feature) — CEP cache + aggregation, wired into /api/mapa
  geocode_all.py  — Standalone script to pre-geocode ALL distinct CEPs on the VM (see Map below)
  auth.py         — JWT authentication
  billing.py      — Stripe billing integration
  itbi.db         — SQLite database (not committed; generated by scraper)
  cache/          — Downloaded XLSX + per-sheet CSV cache (not committed)
frontend/
  index.html      — Single-file SPA (vanilla JS + Chart.js) — main dashboard, served by FastAPI
  admin.html      — Single-file admin SPA (Usuários/Cupons/Atualizar dados) — see "Admin panel" below
landing/
  Next.js app (separate project, App Router + Tailwind + Framer Motion) — marketing landing page.
  Deployed as a static export at the domain root (see "URL structure" above). Local dev:
  npm run dev --prefix landing (port 3000), or via .claude/launch.json preview config ("landing").
  Login/pricing CTAs link to /dashboard. components/Pricing.tsx shows the real live price
  (R$49,90 base, struck through, with the ITBIREMAX30 promo price/coupon/expiry below it —
  static marketing copy, not wired to the Stripe API, see Authentication & billing above).
  app/icon.png (not app/favicon.ico, which was deleted) is the site favicon — Next.js's
  App Router file-convention auto-serves any app/icon.(png|svg|ico) without code changes;
  the old app/favicon.ico was the default create-next-app/Vercel triangle placeholder.
```

### Data flow

1. `scraper_csv.py` resolves each year's URL from the `ARQUIVOS` dict. For the **current year** the URL is fetched dynamically from the official page (`buscar_url_dinamica`) because the filename changes on each update; other years use the fixed URL.
2. Each XLSX has monthly sheets (e.g. `JAN-2025` … `DEZ-2025`). Sheets are read one at a time and cached as CSV in `cache/csv/`.
3. Column names vary wildly across years — `COL_MAP` normalizes ~80 variants to canonical names.
4. Data is saved to the `transacoes` table (delete-then-insert per year); processed file hashes stored in `arquivos_processados` to skip unchanged files.
5. `main.py` startup creates indexes, enables WAL mode, and pre-warms the `/api/resumo` cache in a background thread. A secondary `iptu` table is populated lazily from `transacoes`, keyed by `sql_terreno`.

### Scraper: year is read from the sheet tab name

`scraper_csv.py` determines each record's **year from the sheet tab name** (`ano_da_aba`, e.g. `JAN-2025` → 2025), not from the year "slot". `salvar_no_banco` then deletes/inserts by the actual years present in the DataFrame. This prevents the class of bug where a file published out of order (the 2025 consolidated file is published in Jan 2026, and the current-year file is a `documents/d/fazenda/...` link with no year) lands in the wrong slot and gets stamped with the wrong year. The dynamic-URL override is applied **only to the current year** — never to the previous year — so the previous year always uses its correct fixed URL.

Current dataset: **~2.59M transactions, full historical range 2006–2026** (confirmed via `/api/status`; the `~539k` figure from an earlier session only covered the 2024–2026 initial load — the archive has since been fully backfilled).

### Map / geocoding

- `/api/mapa` and `/api/mapa/status` (in `main.py`) are wired to `geo.py`'s `pontos_mapa()` / `status_geocoding()`. They **only read the `geo_cache` SQLite table** — the on-demand background-geocoding trigger that used to fire when a visitor opened the map was **removed** (see `pontos_mapa()` in `geo.py`) so that live traffic never causes outbound geocoding requests.
- `pontos_mapa()` aggregates transactions by CEP (`GROUP BY`, `LEFT JOIN geo_cache`), respects the active dashboard filters, and has no LIMIT cap (previously hardcoded to 2000, which silently excluded ~39k of the ~41k distinct CEPs — fixed).
- **All geocoding now happens via `backend/geocode_all.py`**, a standalone script run directly on the VPS (not through the API), independent of site traffic. It supports **sharding** to run several instances in parallel:
  ```bash
  # 3 parallel workers, each takes 1/3 of the still-ungeocoded CEPs
  nohup python3 geocode_all.py 0 3 > shard0.log 2>&1 &
  nohup python3 geocode_all.py 1 3 > shard1.log 2>&1 &
  nohup python3 geocode_all.py 2 3 > shard2.log 2>&1 &
  ```
  Each shard re-queries "CEPs not yet in `geo_cache`" at startup and filters by `index % total_shards == shard_id`, so it's safe to kill and relaunch with a different shard count at any time — already-cached CEPs are always skipped (idempotent). SQLite WAL mode (enabled at `main.py` startup) makes concurrent writes from multiple shard processes safe.
  - Rate limit is ~0.15s/CEP + BrasilAPI (primary) → Nominatim (fallback, +0.3s) when BrasilAPI has no coords. A single-process run measured ~3.9s/CEP in practice (many CEPs fall through to the slower Nominatim path), so **parallel shards are the expected way to run this**, not a single process.
  - The script exits on its own once its shard is done — it is not a cron/loop, so once fully geocoded there is no further background activity from it.
- To check progress on the VPS: `tail -n 20 /root/geocode_shard{0,1,2}.log` and `pgrep -f geocode_all.py`.

### Map ↔ table selection, and the map's own independent filter bar

- **Selection drives the map:** when rows are checked in the transactions table (`selectedIds`), `carregarPontos()` (in `frontend/index.html`) fetches `/api/mapa?ids=<comma-joined ids>` instead of the usual filter params — the map then shows *only* the selected transactions' points. This is wired through `applySelectionToKPI()` (already called on every checkbox change), which now also calls `carregarPontos()` when the map is visible. Selection always wins over the map's own filter bar below when both are present.
- **The map's filter bar** (Logradouro/Bairro/CEP/Número, above the Leaflet canvas) is a **separate, independent filter state** from the main dashboard filter panel — searching there does not touch the transactions table/charts, and vice versa. It reuses the same tag-input/chip component (`_initTagInput`) as the main panel (ids `map-rua`/`map-bairro`/`map-cep`/`map-numero`, backed by `_getMapaParams()` which calls `_getTagValue()` on each). Because chips support comma-separated multi-value, `geo.py`'s `pontos_mapa()` needed its own `_multi_like()` OR-clause helper added (mirrors `main.py`'s but is a local closure inside `pontos_mapa()`, since `geo.py` doesn't share `main.py`'s DB connection/UDF setup) — previously the map endpoint only supported one value per field.
- **Map popup quick filters:** each Leaflet circle-marker popup (built in `carregarPontos()`) has three buttons — Bairro / CEP / Logradouro — that call `filtrarPorBairro()`/`filtrarPorCEP()`/`filtrarPorLogradouro()`. These add a chip to *both* the main panel's field and the map's own field (via `_addTag`) and then call `buscar(1)` (updates table/charts) followed by `carregarPontos()` (updates the map), so clicking a popup button is the one place that intentionally bridges the two otherwise-independent filter states. Requires `geo.py`'s point aggregation to expose a representative `logradouro` per CEP group (`MAX(t.logradouro) AS logradouro_db`) alongside the existing `bairro`.
- **Leaflet z-index conflict:** the shared `.acl` autocomplete-dropdown class had `z-index:99`, which rendered *behind* Leaflet's internal panes (popup pane is `z-index:700`) whenever a dropdown was positioned over the map canvas — invisible-but-present bug, only noticeable for the map's own filter fields (the main panel's dropdowns are never near the Leaflet DOM). Fixed by raising `.acl` to `z-index:850`.
- **Autocomplete "stays open + shows ✓" fix:** `_appendItems()` (shared by every tag-input field, main panel and map alike) used to call `lst.style.display='none'` immediately after adding a tag on the *first* selection of an item — closing the dropdown before the checkmark could ever render, which broke fluid multi-select (you had to reopen the field to see the ✓ and pick a second item). Now it re-fetches/re-renders the same query (`_fetchAc(_acQ,true)`) instead of closing, so the dropdown stays open and the ✓ appears immediately — applies to every tag-input field in the app (Logradouro, Bairro, CEP, IPTU, Número, and the map's own fields).

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/transacoes` | Paginated transaction search with filters |
| GET | `/api/resumo` | Aggregated stats (cached 5 min in-memory) |
| GET | `/api/autocomplete/{logradouro,bairro,cep,sql,numero}` | Suggestions (paginated, `offset` param) |
| GET | `/api/iptu/{sql_terreno}` | Property cadastral data |
| GET | `/api/exportar/{excel,pdf}` | Export filtered results |
| GET | `/api/status` | DB record count and processed years |
| POST | `/api/sincronizar` | Trigger scraper in background |
| GET | `/api/mapa` | Geocoded points aggregated by CEP, respects active filters, cache-only (see Map/geocoding above) |
| GET | `/api/mapa/status` | Global geocoding cache status (`rodando`/`pendentes`/`ok`/`falha`) |
| GET/PUT | `/api/usuario/perfil` | Self-service: view/edit own nome/sobrenome/telefone |
| POST | `/api/usuario/trocar-email` | Request e-mail change (confirmation link sent to new address) |
| GET | `/api/auth/confirmar-troca-email` | Public — confirms a pending e-mail change from the link |
| POST | `/api/usuario/trocar-senha` | Self-service password change (requires current password) |
| GET/POST | `/api/admin/usuarios`, `/api/admin/cupons` | Admin panel — see "Admin panel" above for the full endpoint set (desativar/reativar/excluir/perfil/cupons/sincronizar) |

### Key implementation details

- **SQL injection protection**: `buscar_transacoes` uses a whitelist (`COLS_PERMITIDAS`) for sort column; all filters use parameterized queries
- **Multi-value filters**: `_multi_like()` splits comma-separated values into OR clauses (e.g., `bairro=pinheiros,vila madalena`)
- **CEP/SQL normalization**: strips punctuation before comparison so `02806-000` matches `02806000`
- **`/api/resumo` cache**: dict with 5-minute TTL; cache key is the WHERE clause + params string
- **Autocomplete cache**: all distinct values loaded into Python lists at startup — filtering in Python with no DB hits per keystroke; falls back to DB if cache not yet loaded
- **Prewarm**: `_prewarm()` calls `resumo()` directly (not via HTTP) so the full result (incl. `por_mes`, `faixas_valor`) is cached for the default (3yr), all years, and old years ranges
- **Frontend served by FastAPI**: `StaticFiles` mount — registered last so it doesn't shadow API routes
- **Frontend API base**: `const API = location.origin` — must include the port; using `location.hostname` alone drops `:8000` and makes every API call fail (falls back to demo data). `frontend/login.html` has its **own separate** `const API = ...` line (not shared with `index.html`) and had regressed to the `location.hostname`-only version independently — if this bug resurfaces, check *both* files, they don't share the constant.
- **Auth bypass for localhost**: middleware checks `request.client.host in ("127.0.0.1", "::1")` — no token needed locally
- **`.dev_local` flag**: disables the `_popular_iptu_lazy` background thread locally to avoid slow startup
- **Show/hide password toggle**: `login.html` wraps every `<input type="password">` (login, cadastro's confirm-senha, and both fields of redefinir-senha) in a `.pw-wrap` div with an eye-icon `.pw-toggle` button; `toggleSenha(id, btn)` flips `input.type` between `password`/`text` and swaps the SVG icon (`.shown` class). Each of the 4 fields toggles independently.
- **Map filter bar labels**: the 4 map filter fields (Logradouro/Bairro/CEP/Número, `.map-ffield`) originally had no `<label>` above the input — only a "Digite e selecione..." placeholder — unlike the main filter panel's `.ffield` which always has one. Fixed by adding matching `<label>`s and giving `.map-ffield` the same `flex-direction:column` layout as `.ffield`. If more filter fields get added anywhere in the app, always pair them with a `<label>`, not just a placeholder — it silently reads as "unlabeled" otherwise.

### PDF export theme (`exportar.py`)

`gerar_pdf()` uses a **light color palette** (white background, dark navy/blue-ish text, saturated accent colors for KPI cards and charts) — it was originally dark-themed (black background, coral accents, matching the dashboard's dark mode) but that made the exported PDF unreadable/unprofessional for printing, so it was fully converted. The palette lives in a handful of module-level constants near the top of the file (`_BG`, `_SURFACE`, `_SURFACE2`, `_NAVY`, `_INK`, `_INK2`, `_MU`, `_LINE`, `_BLUE`, `_GREEN`, `_PURPLE`, `_AMBER`, `_TEAL`, `_CHART_COLORS`) — almost everything else in the ~600-line PDF builder (KPI cards, table styles, matplotlib chart styling via `_ax_style`, the per-transaction "ficha" detail cards) references these constants rather than hardcoding hex values, so retheming again is mostly a matter of redefining that block. The few spots that *did* have hardcoded hex outside the palette (the top header bar's fill/text color in `_draw_page`, the 5 KPI card tuples, `plt.style.use(...)`, `FIG_BG`) were converted individually — check those specifically if the theme ever needs to change again, `grep` for stray `#` hex literals outside the constants block to catch anything missed.

### Dev/test workflow — isolated copy on the VPS (port 8001)

For risky changes to code that's hard/impossible to test locally without the real 2.59M-row database (map behavior, PDF rendering against real data, anything touching `geo.py`), the established pattern this session is: `cp -a /root/ITBISP /root/ITBISP-dev` (full copy — `itbi.db`, `venv/`, `cache/`, `.env` all come along, no re-scraping or `pip install` needed), then `git checkout <feature-branch>` inside that copy (only tracked files change; the untracked/gitignored data files are left untouched), then run `uvicorn` on port **8001** via `nohup ... & disown` (not a systemd service — just a background process, killed with `fuser -k 8001/tcp` before restarting). The copy shares the *same* `usuarios`/`assinaturas` tables as production (it's a byte-for-byte copy), so the existing admin account or a disposable test account (created via `/api/auth/registrar` then flipped to `assinaturas.status='dev'` with a direct one-off `sqlite3` UPDATE *against the dev copy's own db file only*) can log in normally through the real auth flow to test authenticated features. Delete `/root/ITBISP-dev` and kill its port-8001 process once a feature is merged and deployed — it's disposable and doesn't need to persist between sessions.

**Local tooling added to the user's Windows machine this session** (previously absent): **Node.js LTS** (via `winget install OpenJS.NodeJS.LTS`, needed to `npm run build` the `landing/` Next.js project before each SFTP deploy) and Python's `paramiko` (`py -m pip install paramiko`, needed for the VPS SSH pattern below since Git Bash lacks `sshpass`). **`poppler-utils`** (`pdftoppm`) was installed on the **VPS** (not locally) to render a PDF page to PNG for one-off visual QA of the `exportar.py` redesign — harmless to leave installed, not part of the regular deploy path.

## Git

- `v1-stable` — commit `ac4ce66`, stable state before v2 session changes
- `main` — current v2 with autocomplete, glass popup, tag filters, cache fixes, the year-from-tab scraper fix, the reactivated/fixed map (`/api/mapa`), the `landing/` Next.js project, the map↔selection integration + independent map filter bar, the light-themed PDF export, the ITBIREMAX30 Stripe promo (now R$29,90, managed from the admin panel), the login.html show/hide password toggle, the expanded `admin.html` (cupons/soft-delete/hard-delete/sync trigger, see "Admin panel" above), and the user self-service profile center in `index.html` ("Minha conta", see above)
- Feature branches for this session's riskier changes (`feat/mapa-selecao-integrada`, `fix/pdf-tema-claro`) were fast-forward-merged into `main` after testing on the isolated VPS dev copy (see "Dev/test workflow" above) — safe to delete, their commits are already in `main`'s history
- Repo also has several **untracked legacy/stray files at the root** (`main.py`, `geo.py`, `scraper.py`, `exportar.py`, old `index.html`, `backup-v1/`, etc.) from a pre-`backend/` layout — do not confuse these with the real `backend/*.py` files. `.claude/launch.json`'s uvicorn config uses `--app-dir backend` specifically to avoid accidentally importing these root-level stragglers.
