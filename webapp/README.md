# Dashboard Web - Retencao Cell2Cell

Next.js 16 (App Router, TypeScript, Tailwind v4) + FastAPI (Python) como
serverless function. Login com usuario padrao e sessao JWT em cookie httpOnly.

## Arquitetura

```
app/            paginas Next (login + dashboard protegido)
components/     KPIs, matriz de confusao, graficos (recharts), dashboard
proxy.ts        autenticacao: verifica o JWT e redireciona para /login
api/index.py    backend FastAPI: /api/py/login|logout|dashboard|metrics
api/_dashboard_data.py  dados pre-computados do modelo (gerado, nao editar)
```

Os dados do modelo sao pre-computados por `src/export_dashboard_data.py`
(na raiz do repositorio) - a function Python nao carrega pandas/xgboost,
ficando leve para o limite da Vercel. Apos retreinar o modelo, rode o
script de novo e faca redeploy.

## Rodar local

```powershell
# terminal 1 - backend
cd D:\Churn\webapp
D:\Churn\.venv\Scripts\python.exe -m uvicorn api.index:app --port 8000

# terminal 2 - frontend (proxy /api/py -> 8000 em dev)
npm run dev
```

Login dev: usuario `admin`, senha `trocar123` (fallback so de desenvolvimento).

## Deploy na Vercel

1. Suba o repositorio para o GitHub e importe na Vercel com
   **Root Directory = `webapp`** (framework Next.js e detectado sozinho;
   o `api/index.py` vira function Python automaticamente).
2. Em Settings -> Environment Variables, defina:
   - `DASH_USER` - usuario do login (ex.: `admin`)
   - `DASH_PASSWORD` - a senha real (nunca commitar)
   - `JWT_SECRET` - segredo forte (ex.: `openssl rand -hex 32`),
     usado pelo front (proxy.ts) e pelo back (api/index.py)
3. Deploy. O rewrite de `vercel.json` direciona `/api/py/*` para o FastAPI.

Sem `DASH_PASSWORD`/`JWT_SECRET` configurados, o app usa fallbacks de
desenvolvimento - nao publique assim.
