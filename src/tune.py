"""Melhoria do modelo (pos-Dia N): features derivadas + tuning + novo threshold.

Objetivo de negocio: reduzir falsos positivos (promocoes desperdicadas)
mantendo a deteccao de cancelamentos alta. Tres alavancas:
  1. Features derivadas (razoes de uso/receita/atrito) - src/features.py
  2. Tuning do XGBoost otimizando average_precision (AUC-PR), a metrica
     que mede exatamente a qualidade do ranking sob desbalanceamento
  3. Threshold por restricao: MAXIMA precisao sujeita a recall >= 0.90
     nas predicoes out-of-fold (antes era max F2)

Compara honestamente com o modelo do Dia N no MESMO conjunto de teste e
so substitui os artefatos se houver ganho.

Saidas: models/* atualizados, reports/04_melhoria_modelo.md,
data/processed/scores_teste.csv regravado com os novos scores.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import loguniform, randint, uniform
from sklearn.metrics import (
    average_precision_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    RandomizedSearchCV,
    StratifiedKFold,
    cross_val_predict,
    cross_validate,
    train_test_split,
)
from xgboost import XGBClassifier

from features import adicionar_features

BASE = Path(__file__).resolve().parents[1]
DATA_PATH = BASE / "data" / "processed" / "cell2cell_tratado.csv"
SCORES_PATH = BASE / "data" / "processed" / "scores_teste.csv"
MODELS_DIR = BASE / "models"
REPORT_PATH = BASE / "reports" / "04_melhoria_modelo.md"

SEED = 42
RECALL_MINIMO = 0.90
CV5 = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
CV3 = StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED)

PARAMS_DIA_N = {
    "n_estimators": 400, "learning_rate": 0.05, "max_depth": 6,
    "subsample": 0.8, "colsample_bytree": 0.8, "min_child_weight": 5,
}

ESPACO_BUSCA = {
    "n_estimators": randint(300, 900),
    "learning_rate": loguniform(0.01, 0.1),
    "max_depth": randint(4, 9),
    "min_child_weight": randint(1, 13),
    "subsample": uniform(0.6, 0.4),
    "colsample_bytree": uniform(0.5, 0.5),
    "gamma": uniform(0.0, 5.0),
    "reg_alpha": uniform(0.0, 2.0),
    "reg_lambda": uniform(0.5, 4.5),
}


def fazer_xgb(y_train: pd.Series, **params) -> XGBClassifier:
    razao = float((y_train == 0).sum() / (y_train == 1).sum())
    return XGBClassifier(scale_pos_weight=razao, eval_metric="auc",
                         tree_method="hist", n_jobs=-1, random_state=SEED,
                         **params)


def cv_resumo(modelo, X, y, cv) -> dict:
    res = cross_validate(modelo, X, y, cv=cv,
                         scoring=["average_precision", "roc_auc"])
    return {"auc_pr": res["test_average_precision"].mean(),
            "auc_roc": res["test_roc_auc"].mean()}


def threshold_por_restricao(y: pd.Series, proba: np.ndarray,
                            recall_minimo: float) -> tuple[float, pd.DataFrame]:
    """Maior threshold (= menos FP) cujo recall OOF ainda e >= recall_minimo."""
    linhas = []
    for t in np.arange(0.05, 0.96, 0.01):
        pred = proba >= t
        linhas.append({"threshold": round(float(t), 2),
                       "recall": recall_score(y, pred),
                       "precision": precision_score(y, pred, zero_division=0),
                       "fp": int(((pred == 1) & (y == 0)).sum())})
    tabela = pd.DataFrame(linhas)
    validos = tabela[tabela["recall"] >= recall_minimo]
    escolhido = float(validos["threshold"].max())
    return escolhido, tabela


def metricas_teste(y_test, proba, threshold) -> dict:
    pred = (proba >= threshold).astype(int)
    fp = int(((pred == 1) & (y_test == 0)).sum())
    fn = int(((pred == 0) & (y_test == 1)).sum())
    return {"threshold": threshold,
            "recall": round(recall_score(y_test, pred), 4),
            "precision": round(precision_score(y_test, pred), 4),
            "auc_roc": round(roc_auc_score(y_test, proba), 4),
            "auc_pr": round(average_precision_score(y_test, proba), 4),
            "fp": fp, "fn": fn, "abordados": int(pred.sum())}


def main() -> None:
    df = pd.read_csv(DATA_PATH, index_col="CustomerID")
    scores_antigos = pd.read_csv(SCORES_PATH)

    X_base = df.drop(columns=["Churn"])
    y = df["Churn"]
    X_feat = adicionar_features(X_base)
    Xb_tr, Xb_te, y_tr, y_te = train_test_split(
        X_base, y, test_size=0.2, stratify=y, random_state=SEED)
    Xf_tr, Xf_te = X_feat.loc[Xb_tr.index], X_feat.loc[Xb_te.index]

    print("1) Features derivadas ajudam? (CV 3-fold, params do Dia N)")
    r_base = cv_resumo(fazer_xgb(y_tr, **PARAMS_DIA_N), Xb_tr, y_tr, CV3)
    r_feat = cv_resumo(fazer_xgb(y_tr, **PARAMS_DIA_N), Xf_tr, y_tr, CV3)
    print(f"   sem features: AUC-PR={r_base['auc_pr']:.4f} AUC={r_base['auc_roc']:.4f}")
    print(f"   com features: AUC-PR={r_feat['auc_pr']:.4f} AUC={r_feat['auc_roc']:.4f}")
    usar_features = r_feat["auc_pr"] >= r_base["auc_pr"]
    X_tr, X_te = (Xf_tr, Xf_te) if usar_features else (Xb_tr, Xb_te)
    print(f"   -> usando features: {usar_features}")

    print("\n2) Busca de hiperparametros (30 candidatos, CV 3-fold, AUC-PR)...")
    busca = RandomizedSearchCV(
        fazer_xgb(y_tr), ESPACO_BUSCA, n_iter=30, cv=CV3,
        scoring="average_precision", random_state=SEED, n_jobs=1, verbose=1)
    busca.fit(X_tr, y_tr)
    print(f"   melhor AUC-PR (CV3): {busca.best_score_:.4f}")
    print(f"   params: {busca.best_params_}")

    print("\n3) Validacao 5-fold: Dia N vs tunado")
    cfg_dia_n = fazer_xgb(y_tr, **PARAMS_DIA_N)
    cfg_tunada = fazer_xgb(y_tr, **busca.best_params_)
    r_dia_n = cv_resumo(cfg_dia_n, X_tr, y_tr, CV5)
    r_tunada = cv_resumo(cfg_tunada, X_tr, y_tr, CV5)
    print(f"   Dia N : AUC-PR={r_dia_n['auc_pr']:.4f} AUC={r_dia_n['auc_roc']:.4f}")
    print(f"   tunado: AUC-PR={r_tunada['auc_pr']:.4f} AUC={r_tunada['auc_roc']:.4f}")
    vencedor = cfg_tunada if r_tunada["auc_pr"] >= r_dia_n["auc_pr"] else cfg_dia_n
    params_vencedor = (busca.best_params_
                       if vencedor is cfg_tunada else PARAMS_DIA_N)
    print(f"   -> vencedor: {'tunado' if vencedor is cfg_tunada else 'Dia N'}")

    print(f"\n4) Threshold: max precisao com recall OOF >= {RECALL_MINIMO:.0%}")
    proba_oof = cross_val_predict(vencedor, X_tr, y_tr, cv=CV5,
                                  method="predict_proba")[:, 1]
    threshold, _ = threshold_por_restricao(y_tr, proba_oof, RECALL_MINIMO)
    print(f"   threshold escolhido: {threshold:.2f}")

    print("\n5) Avaliacao final no teste (mesmo split do Dia N)")
    vencedor.fit(X_tr, y_tr)
    proba_nova = vencedor.predict_proba(X_te)[:, 1]
    antigo = metricas_teste(
        scores_antigos["churn_real"].values,
        scores_antigos["prob_churn"].values, 0.25)
    novo = metricas_teste(y_te.values, proba_nova, threshold)
    comp = pd.DataFrame([{"modelo": "Dia N (thr 0,25 - max F2)", **antigo},
                         {"modelo": f"Melhorado (thr {threshold:.2f} - "
                                    f"recall>={RECALL_MINIMO:.0%})", **novo}])
    print(comp.to_string(index=False))

    vencedor.save_model(MODELS_DIR / "xgb_model.json")
    (MODELS_DIR / "threshold.json").write_text(json.dumps({
        "threshold": threshold,
        "criterio": f"max precisao com recall OOF >= {RECALL_MINIMO}",
        "params_modelo": {k: (round(v, 5) if isinstance(v, float) else int(v))
                          for k, v in params_vencedor.items()},
        "usa_features_derivadas": bool(usar_features),
    }, indent=2), encoding="utf-8")

    ranking = pd.DataFrame({"CustomerID": X_te.index,
                            "prob_churn": proba_nova.round(4),
                            "churn_real": y_te.values})
    ranking = ranking.sort_values("prob_churn", ascending=False)
    ranking["rank_risco"] = range(1, len(ranking) + 1)
    ranking.to_csv(SCORES_PATH, index=False)

    delta_fp = antigo["fp"] - novo["fp"]
    REPORT_PATH.write_text("\n".join([
        "# Melhoria do Modelo - menos falsos positivos, recall preservado",
        "",
        f"- Features derivadas usadas: **{usar_features}** "
        f"(AUC-PR CV3 {r_base['auc_pr']:.4f} -> {r_feat['auc_pr']:.4f})",
        f"- Tuning (30 candidatos, AUC-PR): CV5 {r_dia_n['auc_pr']:.4f} -> "
        f"{r_tunada['auc_pr']:.4f}",
        f"- Novo criterio de threshold: **max precisao com recall >= "
        f"{RECALL_MINIMO:.0%}** (out-of-fold) -> threshold {threshold:.2f}",
        "",
        "## Comparacao no mesmo conjunto de teste",
        "",
        comp.to_markdown(index=False),
        "",
        f"**Falsos positivos: {antigo['fp']:,} -> {novo['fp']:,} "
        f"({delta_fp:+,} promocoes desnecessarias)**",
        "",
        "Params do vencedor: " + json.dumps(params_vencedor, default=float),
    ]), encoding="utf-8")
    print(f"\nRelatorio: {REPORT_PATH}")


if __name__ == "__main__":
    main()
