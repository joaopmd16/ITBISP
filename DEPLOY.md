# 🚀 Deploy — ITBI Dashboard SP

## Deploy em produção (Railway + Vercel)

### 1. Sobe o código no GitHub

```bash
git init
git add .
git commit -m "ITBI Dashboard v2"
git remote add origin https://github.com/SEU_USUARIO/itbi-dashboard.git
git push -u origin main
```

---

### 2. Backend no Railway

1. Acesse [railway.app](https://railway.app) e crie uma conta
2. Clique em **"New Project"** → **"Deploy from GitHub repo"**
3. Selecione o repositório `itbi-dashboard`
4. Railway detecta o `nixpacks.toml` automaticamente

**Adicione o banco PostgreSQL:**
- No projeto Railway, clique em **"+ New"** → **"Database"** → **"PostgreSQL"**
- Clique no PostgreSQL criado → **"Connect"** → copie a `DATABASE_URL`

**Configure a variável de ambiente:**
- No serviço da API → **"Variables"** → **"+ New Variable"**
- Nome: `DATABASE_URL`
- Valor: cole a URL copiada acima

**Pronto!** Railway faz deploy automático. Você recebe uma URL tipo:
`https://itbi-dashboard-production.up.railway.app`

---

### 3. Frontend na Vercel

1. Acesse [vercel.com](https://vercel.com) e crie uma conta
2. **"New Project"** → importa o mesmo repositório
3. Configure:
   - **Root Directory:** `frontend`
   - **Framework:** Other (HTML estático)
4. Deploy!

Você recebe uma URL tipo: `https://itbi-dashboard.vercel.app`

---

### 4. Popular o banco com dados

Com o Railway rodando, conecte o scraper ao banco de produção:

```bash
# No .env local, coloque a DATABASE_URL do Railway
DATABASE_URL=postgresql://... python scraper.py --forcar
```

Ou no Git Bash:
```bash
set DATABASE_URL=postgresql://...
python scraper.py --forcar
```

---

## Desenvolvimento local

```bash
# Sem DATABASE_URL = usa SQLite automaticamente
cd backend
python -m uvicorn main:app --reload

# Abre o frontend
start frontend/index.html
```

---

## Variáveis de ambiente

| Variável | Descrição | Obrigatória em prod |
|---|---|---|
| `DATABASE_URL` | URL PostgreSQL do Railway | ✅ |
| `PORT` | Porta (Railway define automaticamente) | ❌ |
