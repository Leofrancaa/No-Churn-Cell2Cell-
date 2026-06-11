"""Backend do dashboard (FastAPI rodando como serverless function na Vercel).

Rotas sob /api/py/*:
  POST /api/py/login       -> valida credenciais e grava cookie JWT httpOnly
  POST /api/py/logout      -> remove o cookie
  GET  /api/py/dashboard   -> payload completo (meta, roc, distribuicao, ...)
  GET  /api/py/metrics     -> metricas recalculadas para um threshold

Credenciais e segredo vem de variaveis de ambiente (ver .env.example).
Os dados do modelo sao pre-computados em _dashboard_data.py - a function
nao carrega pandas/xgboost, ficando leve para o deploy.
"""

from __future__ import annotations

import hmac
import os
import time

import jwt
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

try:  # execucao na Vercel (raiz do projeto) vs uvicorn local (pacote api.)
    from api._dashboard_data import DATA
except ImportError:
    from _dashboard_data import DATA

USUARIO_PADRAO = os.environ.get("DASH_USER", "admin")
# Em producao, defina DASH_PASSWORD no painel da Vercel. O fallback existe
# apenas para desenvolvimento local e deve ser trocado antes do deploy.
SENHA = os.environ.get("DASH_PASSWORD", "trocar123")
SEGREDO_JWT = os.environ.get("JWT_SECRET", "dev-secret-trocar-no-deploy")
VALIDADE_SESSAO_S = 8 * 3600
COOKIE = "session"

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class Credenciais(BaseModel):
    username: str
    password: str


def emitir_token(usuario: str) -> str:
    agora = int(time.time())
    return jwt.encode({"sub": usuario, "iat": agora, "exp": agora + VALIDADE_SESSAO_S},
                      SEGREDO_JWT, algorithm="HS256")


def exigir_sessao(request: Request) -> str:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Nao autenticado")
    try:
        payload = jwt.decode(token, SEGREDO_JWT, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Sessao invalida") from exc
    return str(payload["sub"])


def metricas_no_threshold(threshold: float) -> dict:
    prob = DATA["scores"]["prob"]
    real = DATA["scores"]["real"]
    tp = fp = tn = fn = 0
    for p, r in zip(prob, real):
        previsto = p >= threshold
        if previsto and r:
            tp += 1
        elif previsto:
            fp += 1
        elif r:
            fn += 1
        else:
            tn += 1
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    precisao = tp / (tp + fp) if (tp + fp) else 0.0
    f1 = (2 * precisao * recall / (precisao + recall)) if (precisao + recall) else 0.0
    return {
        "threshold": threshold,
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "recall": round(recall, 4),
        "precision": round(precisao, 4),
        "f1": round(f1, 4),
        "abordados": tp + fp,
    }


@app.post("/api/py/login")
def login(cred: Credenciais, response: Response) -> dict:
    usuario_ok = hmac.compare_digest(cred.username.strip(), USUARIO_PADRAO)
    senha_ok = hmac.compare_digest(cred.password, SENHA)
    if not (usuario_ok and senha_ok):
        raise HTTPException(status_code=401, detail="Usuario ou senha incorretos")
    response.set_cookie(
        COOKIE, emitir_token(cred.username.strip()),
        max_age=VALIDADE_SESSAO_S, httponly=True, samesite="lax",
        secure=os.environ.get("VERCEL") == "1", path="/",
    )
    return {"ok": True, "user": cred.username.strip()}


@app.post("/api/py/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@app.get("/api/py/dashboard")
def dashboard(request: Request) -> dict:
    exigir_sessao(request)
    thr = DATA["meta"]["threshold_oficial"]
    return {
        "meta": DATA["meta"],
        "roc": DATA["roc"],
        "distribuicao": DATA["distribuicao"],
        "importancias": DATA["importancias"],
        "ranking": DATA["ranking"][:25],
        "metricas": metricas_no_threshold(thr),
    }


@app.get("/api/py/metrics")
def metrics(request: Request, threshold: float = 0.25) -> dict:
    exigir_sessao(request)
    if not 0.0 < threshold < 1.0:
        raise HTTPException(status_code=422, detail="threshold deve estar entre 0 e 1")
    return metricas_no_threshold(round(threshold, 2))
