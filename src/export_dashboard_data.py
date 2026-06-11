"""Exporta os artefatos do Dia N para o backend do dashboard web.

Pre-computa tudo que exige pandas/sklearn/xgboost (ROC, histograma,
importancias) e grava como modulo Python puro em webapp/api/_dashboard_data.py.
Assim a serverless function da Vercel fica leve (so FastAPI + stdlib) e o
modelo nunca precisa rodar no deploy.

Os scores individuais (prob, real) vao juntos: sao ~10 mil pares, o que
permite recalcular a matriz de confusao para qualquer threshold em puro
Python no backend.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve
from xgboost import XGBClassifier

BASE = Path(__file__).resolve().parents[1]
SCORES_PATH = BASE / "data" / "processed" / "scores_teste.csv"
THRESHOLD_PATH = BASE / "models" / "threshold.json"
XGB_PATH = BASE / "models" / "xgb_model.json"
OUT_PATH = BASE / "webapp" / "api" / "_dashboard_data.py"


def curva_roc_reduzida(y: np.ndarray, proba: np.ndarray, max_pontos: int = 200) -> list:
    fpr, tpr, _ = roc_curve(y, proba)
    if len(fpr) > max_pontos:
        idx = np.linspace(0, len(fpr) - 1, max_pontos).astype(int)
        fpr, tpr = fpr[idx], tpr[idx]
    return [{"fpr": round(float(f), 4), "tpr": round(float(t), 4)}
            for f, t in zip(fpr, tpr)]


def histograma_por_classe(df: pd.DataFrame, bins: int = 40) -> list:
    bordas = np.linspace(0, 1, bins + 1)
    centros = (bordas[:-1] + bordas[1:]) / 2
    h_fica, _ = np.histogram(df.loc[df["churn_real"] == 0, "prob_churn"], bins=bordas)
    h_cancela, _ = np.histogram(df.loc[df["churn_real"] == 1, "prob_churn"], bins=bordas)
    return [{"score": round(float(c), 3), "ficou": int(a), "cancelou": int(b)}
            for c, a, b in zip(centros, h_fica, h_cancela)]


def importancias_xgb(top: int = 20) -> list:
    modelo = XGBClassifier()
    modelo.load_model(XGB_PATH)
    ganhos = modelo.get_booster().get_score(importance_type="gain")
    ordenado = sorted(ganhos.items(), key=lambda kv: kv[1], reverse=True)[:top]
    return [{"variavel": nome, "ganho": round(float(v), 2)} for nome, v in ordenado]


def main() -> None:
    df = pd.read_csv(SCORES_PATH)
    threshold = json.loads(THRESHOLD_PATH.read_text(encoding="utf-8"))["threshold"]

    dados = {
        "meta": {
            "auc": round(float(roc_auc_score(df["churn_real"], df["prob_churn"])), 4),
            "threshold_oficial": threshold,
            "n_teste": int(len(df)),
            "taxa_churn": round(float(df["churn_real"].mean()), 4),
        },
        "scores": {
            "prob": [round(float(p), 4) for p in df["prob_churn"]],
            "real": [int(r) for r in df["churn_real"]],
        },
        "roc": curva_roc_reduzida(df["churn_real"].values, df["prob_churn"].values),
        "distribuicao": histograma_por_classe(df),
        "importancias": importancias_xgb(),
        "ranking": df.head(100).to_dict(orient="records"),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    conteudo = (
        '"""Dados pre-computados do modelo (gerado por src/export_dashboard_data.py).\n'
        'Nao editar manualmente."""\n\n'
        f"DATA = {json.dumps(dados, ensure_ascii=False)}\n"
    )
    OUT_PATH.write_text(conteudo, encoding="utf-8")
    print(f"Gerado: {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
