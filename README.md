# 🏠 Dashboard ITBI · São Paulo

Dashboard para consulta das transações imobiliárias com recolhimento de ITBI da Prefeitura de SP.
Dados de **2006 a 2026**, atualizados mensalmente direto da fonte oficial.

---

## 📁 Estrutura do projeto

```
itbi-dashboard/
├── backend/
│   ├── scraper.py          ← Baixa as planilhas e salva no banco
│   ├── main.py             ← API FastAPI (backend)
│   ├── requirements.txt
│   └── itbi.db             ← Banco SQLite (criado automaticamente)
└── frontend/
    └── index.html          ← Dashboard (abre no navegador)
```

---

## 🚀 Como rodar

### 1. Instalar dependências

```bash
cd itbi-dashboard/backend
pip install -r requirements.txt
```

### 2. Baixar os dados (primeira vez)

```bash
# Baixa TODOS os anos (pode demorar 10-20 min, são ~600MB)
python scraper.py

# Ou só os anos recentes para testar rápido:
python scraper.py --anos 2024 2025 2026
```

O scraper é **inteligente**: ele salva um hash de cada arquivo.
Na próxima execução, só reprocessa se o arquivo mudou na prefeitura.

### 3. Subir a API

```bash
uvicorn main:app --reload
# Rodando em: http://localhost:8000
```

### 4. Abrir o dashboard

Abra o arquivo `frontend/index.html` no navegador.
Ou acesse http://localhost:8000/app

---

## 🔄 Atualização automática (mensal)

O arquivo de 2026 é atualizado toda vez que a prefeitura registra novas transações.
Configure um **cron job** para rodar o scraper automaticamente:

### Linux / Mac (crontab)

```bash
crontab -e
```

Adicione (roda todo dia 1 do mês às 6h):
```
0 6 1 * * cd /caminho/para/itbi-dashboard/backend && python scraper.py --anos 2026
```

### Windows (Task Scheduler)

Crie uma tarefa agendada mensal que execute:
```
python C:\caminho\itbi-dashboard\backend\scraper.py --anos 2026
```

### Ou via botão no dashboard

O dashboard tem um botão **"⟳ Sincronizar dados"** que dispara o scraper via API.

---

## 🔍 Funcionalidades do Dashboard

| Funcionalidade | Descrição |
|---|---|
| Busca por logradouro | Autocomplete com todas as ruas |
| Busca por bairro | Autocomplete com todos os bairros |
| Filtro por CEP | Busca por CEP parcial ou completo |
| Filtro por ano | De 2006 até 2026 |
| Filtro por valor | Range de valor declarado |
| KPIs em tempo real | Total, volume, ticket médio, ITBI |
| Gráfico por ano | Volume de transações por ano |
| Top 10 bairros | Bairros com mais transações |
| Tabela paginada | 50 por página, navegação completa |

---

## 🗄️ Estrutura do banco de dados

```sql
CREATE TABLE transacoes (
    id                  INTEGER PRIMARY KEY,
    ano_referencia      INTEGER,   -- Ano de referência
    mes_referencia      INTEGER,   -- Mês de referência (1-12)
    data_transacao      TEXT,      -- Data da transação
    logradouro          TEXT,      -- Nome da rua
    numero              TEXT,      -- Número
    complemento         TEXT,      -- Complemento
    bairro              TEXT,      -- Bairro
    cep                 TEXT,      -- CEP
    sql_terreno         TEXT,      -- SQL (código do imóvel no IPTU)
    area_terreno        REAL,      -- Área do terreno em m²
    area_construida     REAL,      -- Área construída em m²
    valor_declarado     REAL,      -- Valor declarado da transação
    valor_financiado    REAL,      -- Valor financiado
    valor_itbi          REAL,      -- Valor base de cálculo do ITBI
    natureza_transacao  TEXT,      -- Tipo: compra/venda, doação, etc
    tipo_uso            TEXT       -- Residencial, comercial, etc
);
```

---

## 📡 API REST

Com a API rodando, você pode fazer queries diretamente:

```
GET /api/transacoes?logradouro=paulista&ano_min=2020&ano_max=2024
GET /api/resumo?bairro=pinheiros
GET /api/autocomplete/logradouro?q=august
GET /api/status
POST /api/sincronizar
```

Documentação interativa: http://localhost:8000/docs

---

## 💡 Dica: Analisar com Python/Pandas

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('backend/itbi.db')
df = pd.read_sql("SELECT * FROM transacoes WHERE bairro LIKE '%PINHEIROS%'", conn)
print(df.groupby('ano_referencia')['valor_declarado'].agg(['count','mean','sum']))
```
