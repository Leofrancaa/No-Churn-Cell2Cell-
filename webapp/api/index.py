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
import random
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

# Tabelas derivadas dos dados pre-computados (matriz oculta do simulador,
# custo e nome das acoes, ordem de preferencia aprendida por segmento)
TAXA_REAL = {
    seg: {linha["acao"]: linha["taxa_real_oculta"] for linha in linhas}
    for seg, linhas in DATA["retencao"]["politica"].items()
}
ORDEM_APRENDIDA = {
    seg: [linha["acao"] for linha in linhas]
    for seg, linhas in DATA["retencao"]["politica"].items()
}
CUSTO_ACAO = {acao["id"]: acao["custo"] for acao in DATA["retencao"]["acoes"]}
NOME_ACAO = {acao["id"]: acao["nome"] for acao in DATA["retencao"]["acoes"]}

# Premissa documentada: oferta aceita reduz o risco do cliente em 60%
# (a aceitacao real e trabalho futuro - ver reports/05_modulo_retencao.md)
REDUCAO_RISCO_ACEITE = 0.60


class Credenciais(BaseModel):
    username: str
    password: str


class OfertaSimulada(BaseModel):
    customer_id: int
    acao: str | None = None


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


@app.get("/api/py/analista")
def analista(request: Request) -> dict:
    """Dados da visao do analista: fila de retencao, politica e curvas."""
    exigir_sessao(request)
    detalhe = DATA["clientes_detalhe"]
    fila = [{
        "CustomerID": int(cid),
        "prob": info["prob"],
        "rank": info["rank"],
        "segmento": info["segmento"],
        "acao_nome": info["acao_nome"],
        "taxa_esperada": info["taxa_esperada"],
    } for cid, info in detalhe.items()]
    fila.sort(key=lambda c: c["rank"])
    return {
        "meta": DATA["meta"],
        "fila": fila[:200],
        "retencao": DATA["retencao"],
        "shap_global": DATA["shap_global"],
    }


@app.get("/api/py/cliente/{customer_id}")
def cliente(request: Request, customer_id: int) -> dict:
    """Detalhe individual: fatores SHAP, segmento e acao recomendada."""
    exigir_sessao(request)
    info = DATA["clientes_detalhe"].get(str(customer_id))
    if info is None:
        raise HTTPException(
            status_code=404,
            detail="Cliente fora do topo do ranking (detalhe disponivel "
                   f"para os {len(DATA['clientes_detalhe'])} maiores riscos)")
    return {"CustomerID": customer_id, **info}


@app.post("/api/py/simular_oferta")
def simular_oferta(request: Request, oferta: OfertaSimulada) -> dict:
    """Envia uma oferta ao cliente simulado e devolve o desfecho.

    O aceite e sorteado com a probabilidade REAL (oculta) do par
    segmento x acao - o mesmo simulador que treinou o agente.
    """
    exigir_sessao(request)
    info = DATA["clientes_detalhe"].get(str(oferta.customer_id))
    if info is None:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    segmento = info["segmento"]
    acao = oferta.acao or info["acao"]
    if acao not in CUSTO_ACAO:
        raise HTTPException(status_code=422, detail="Acao desconhecida")

    taxa = TAXA_REAL[segmento][acao]
    aceitou = random.random() < taxa
    risco_antes = info["prob"]
    risco_depois = (round(risco_antes * (1 - REDUCAO_RISCO_ACEITE), 4)
                    if aceitou else risco_antes)
    return {
        "CustomerID": oferta.customer_id,
        "segmento": segmento,
        "acao": acao,
        "acao_nome": NOME_ACAO[acao],
        "custo": CUSTO_ACAO[acao],
        "aceitou": aceitou,
        "risco_antes": risco_antes,
        "risco_depois": risco_depois,
        "reducao_risco_aceite": REDUCAO_RISCO_ACEITE,
        "alternativas": ORDEM_APRENDIDA[segmento],
    }


@app.get("/api/py/simular_campanha")
def simular_campanha(request: Request, top_n: int = 200,
                     ltv: float = 500.0) -> dict:
    """Valor esperado de acionar os top N riscos com a politica aprendida.

    Premissas (documentadas no relatorio): salvo = cancelaria (prob) E
    aceita a oferta (taxa real); custo incorre apenas quando a oferta e
    aceita; cliente salvo preserva o LTV informado.
    """
    exigir_sessao(request)
    detalhe = DATA["clientes_detalhe"]
    if not 1 <= top_n <= len(detalhe):
        raise HTTPException(
            status_code=422,
            detail=f"top_n deve estar entre 1 e {len(detalhe)}")
    if not 0 < ltv <= 100_000:
        raise HTTPException(status_code=422, detail="ltv fora do intervalo")

    ordenados = sorted(detalhe.values(), key=lambda c: c["rank"])[:top_n]
    por_segmento: dict[str, dict] = {}
    aceites = salvos = custo = perdidos_sem_acao = 0.0
    for cli in ordenados:
        seg = cli["segmento"]
        acao = cli["acao"]
        taxa = TAXA_REAL[seg][acao]
        agg = por_segmento.setdefault(seg, {
            "segmento": seg, "acao_nome": NOME_ACAO[acao], "clientes": 0,
            "aceites_esperados": 0.0, "salvos_esperados": 0.0, "custo": 0.0,
        })
        agg["clientes"] += 1
        agg["aceites_esperados"] += taxa
        agg["salvos_esperados"] += cli["prob"] * taxa
        agg["custo"] += CUSTO_ACAO[acao] * taxa
        aceites += taxa
        salvos += cli["prob"] * taxa
        custo += CUSTO_ACAO[acao] * taxa
        perdidos_sem_acao += cli["prob"]

    receita_preservada = salvos * ltv
    roi = (receita_preservada - custo) / custo if custo else 0.0
    return {
        "top_n": top_n,
        "ltv": ltv,
        "aceites_esperados": round(aceites, 1),
        "salvos_esperados": round(salvos, 1),
        "perdidos_sem_acao": round(perdidos_sem_acao, 1),
        "custo_esperado": round(custo, 2),
        "receita_preservada": round(receita_preservada, 2),
        "roi": round(roi, 2),
        "por_segmento": [
            {**agg,
             "aceites_esperados": round(agg["aceites_esperados"], 1),
             "salvos_esperados": round(agg["salvos_esperados"], 1),
             "custo": round(agg["custo"], 2)}
            for agg in sorted(por_segmento.values(),
                              key=lambda a: a["clientes"], reverse=True)
        ],
    }
