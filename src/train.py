"""Modulo de Previsao (Dia N) - Cell2Cell.

Treina o baseline (Regressao Logistica) e o modelo principal (XGBoost)
com validacao cruzada estratificada, escolhe o ponto de decisao via
predicoes out-of-fold priorizando a deteccao de cancelamentos (F2),
avalia no conjunto de teste e gera relatorio + graficos + ranking de risco.

Saidas:
  models/logreg.joblib, models/xgb_model.json, models/threshold.json
  reports/03_modulo_previsao.md, reports/figs/*.png
  data/processed/scores_teste.csv (ranking de risco para o dashboard)
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import (
    StratifiedKFold,
    cross_val_predict,
    cross_validate,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

BASE = Path(__file__).resolve().parents[1]
DATA_PATH = BASE / "data" / "processed" / "cell2cell_tratado.csv"
MODELS_DIR = BASE / "models"
FIGS_DIR = BASE / "reports" / "figs"
REPORT_PATH = BASE / "reports" / "03_modulo_previsao.md"
SCORES_PATH = BASE / "data" / "processed" / "scores_teste.csv"

SEED = 42
CV = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
SCORING = ["recall", "f1", "roc_auc", "precision"]


def construir_modelos(y_train: pd.Series) -> dict[str, object]:
    """Baseline com escala + pesos; XGBoost com scale_pos_weight."""
    razao_neg_pos = float((y_train == 0).sum() / (y_train == 1).sum())
    logreg = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced",
                                   random_state=SEED)),
    ])
    xgb = XGBClassifier(
        n_estimators=400, learning_rate=0.05, max_depth=6,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
        scale_pos_weight=razao_neg_pos, eval_metric="auc",
        tree_method="hist", n_jobs=-1, random_state=SEED,
    )
    return {"Regressao Logistica (baseline)": logreg, "XGBoost": xgb}


def validar_cruzado(modelos: dict, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    linhas = []
    for nome, modelo in modelos.items():
        res = cross_validate(modelo, X, y, cv=CV, scoring=SCORING, n_jobs=1)
        linhas.append({
            "modelo": nome,
            **{m: f"{res[f'test_{m}'].mean():.3f} +/- {res[f'test_{m}'].std():.3f}"
               for m in SCORING},
        })
    return pd.DataFrame(linhas)


def escolher_threshold(modelo, X: pd.DataFrame, y: pd.Series) -> tuple[float, pd.DataFrame]:
    """Escolhe o threshold maximizando F2 nas predicoes out-of-fold.

    F2 pesa recall 2x mais que precisao: na otica de negocio, perder um
    cliente (FN) custa muito mais que oferecer promocao a quem ficaria (FP).
    Usa apenas o treino (OOF) para nao vazar o teste.
    """
    proba_oof = cross_val_predict(modelo, X, y, cv=CV, method="predict_proba",
                                  n_jobs=1)[:, 1]
    candidatos = np.arange(0.20, 0.71, 0.05)
    linhas = [{
        "threshold": round(float(t), 2),
        "recall": recall_score(y, proba_oof >= t),
        "precision": precision_score(y, proba_oof >= t),
        "f1": f1_score(y, proba_oof >= t),
        "f2": fbeta_score(y, proba_oof >= t, beta=2),
    } for t in candidatos]
    tabela = pd.DataFrame(linhas).round(3)
    melhor = float(tabela.loc[tabela["f2"].idxmax(), "threshold"])
    return melhor, tabela


def avaliar_teste(nome: str, proba: np.ndarray, y_test: pd.Series,
                  threshold: float) -> dict:
    pred = (proba >= threshold).astype(int)
    return {
        "modelo": nome, "threshold": threshold,
        "recall": round(recall_score(y_test, pred), 3),
        "precision": round(precision_score(y_test, pred), 3),
        "f1": round(f1_score(y_test, pred), 3),
        "auc_roc": round(roc_auc_score(y_test, proba), 3),
        "matriz_confusao": confusion_matrix(y_test, pred).tolist(),
    }


def gerar_figuras(probas: dict[str, np.ndarray], y_test: pd.Series,
                  threshold: float, xgb: XGBClassifier,
                  colunas: list[str]) -> None:
    FIGS_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 6))
    for nome, proba in probas.items():
        fpr, tpr, _ = roc_curve(y_test, proba)
        ax.plot(fpr, tpr, label=f"{nome} (AUC={roc_auc_score(y_test, proba):.3f})")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
    ax.set_xlabel("Taxa de falsos positivos")
    ax.set_ylabel("Taxa de verdadeiros positivos (recall)")
    ax.set_title("Curva ROC - conjunto de teste")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGS_DIR / "roc_teste.png", dpi=120)
    plt.close(fig)

    pred = (probas["XGBoost"] >= threshold).astype(int)
    fig, ax = plt.subplots(figsize=(6, 5))
    ConfusionMatrixDisplay(confusion_matrix(y_test, pred),
                           display_labels=["Fica", "Cancela"]).plot(ax=ax)
    ax.set_title(f"XGBoost no teste (threshold={threshold:.2f})")
    fig.tight_layout()
    fig.savefig(FIGS_DIR / "matriz_confusao_xgb.png", dpi=120)
    plt.close(fig)

    importancia = pd.Series(xgb.feature_importances_, index=colunas)
    top = importancia.sort_values(ascending=True).tail(20)
    fig, ax = plt.subplots(figsize=(8, 7))
    top.plot.barh(ax=ax)
    ax.set_title("XGBoost - 20 variaveis mais importantes (ganho)")
    fig.tight_layout()
    fig.savefig(FIGS_DIR / "importancia_xgb.png", dpi=120)
    plt.close(fig)


def gerar_relatorio(cv_tab: pd.DataFrame, thr_tab: pd.DataFrame,
                    threshold: float, resultados: list[dict],
                    n_train: int, n_test: int) -> str:
    def tabela_md(df: pd.DataFrame) -> str:
        return df.to_markdown(index=False)

    res_df = pd.DataFrame(resultados).drop(columns=["matriz_confusao"])
    mc = next(r for r in resultados
              if r["modelo"] == "XGBoost" and r["threshold"] == threshold)
    tn, fp, fn, tp = np.array(mc["matriz_confusao"]).ravel()
    return "\n".join([
        "# Modulo de Previsao (Dia N) - Resultados",
        "",
        f"- Split estratificado: **{n_train:,} treino / {n_test:,} teste (20%)**, seed 42.",
        "- Validacao cruzada 5-fold estratificada, apenas no treino.",
        "- Desbalanceamento tratado com `class_weight='balanced'` (baseline) e "
        "`scale_pos_weight` (XGBoost) - sem SMOTE: os pesos deram recall "
        "equivalente sem custo extra.",
        "",
        "## Validacao cruzada (5-fold, treino)",
        "",
        tabela_md(cv_tab),
        "",
        "## Ajuste do ponto de decisao (out-of-fold, sem tocar no teste)",
        "",
        "Criterio: maximizar **F2** (recall pesa 2x a precisao), porque perder "
        "um cliente custa mais que oferecer promocao a quem nao cancelaria.",
        "",
        tabela_md(thr_tab),
        "",
        f"**Threshold escolhido: {threshold:.2f}**",
        "",
        "## Avaliacao final no conjunto de teste",
        "",
        tabela_md(res_df),
        "",
        f"Matriz de confusao do XGBoost no threshold {threshold:.2f}: "
        f"TN={tn:,} | FP={fp:,} | FN={fn:,} | TP={tp:,}",
        "",
        "Leitura de negocio: dos clientes que cancelariam, o modelo detecta "
        f"**{tp / (tp + fn):.0%}** (recall). O custo disso sao {fp:,} promocoes "
        "oferecidas a clientes que ficariam - barato comparado a perder "
        f"{tp:,} clientes detectaveis.",
        "",
        "## Artefatos",
        "",
        "- `models/xgb_model.json`, `models/logreg.joblib`, `models/threshold.json`",
        "- `reports/figs/`: curva ROC, matriz de confusao, importancia de variaveis",
        "- `data/processed/scores_teste.csv`: ranking de risco do teste "
        "(insumo do dashboard do Dia H)",
    ])


def main() -> None:
    df = pd.read_csv(DATA_PATH, index_col="CustomerID")
    X = df.drop(columns=["Churn"])
    y = df["Churn"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SEED)

    modelos = construir_modelos(y_train)
    print("Validacao cruzada 5-fold...")
    cv_tab = validar_cruzado(modelos, X_train, y_train)
    print(cv_tab.to_string(index=False))

    print("\nAjustando threshold via predicoes out-of-fold (XGBoost)...")
    threshold, thr_tab = escolher_threshold(modelos["XGBoost"], X_train, y_train)
    print(thr_tab.to_string(index=False))
    print(f"Threshold escolhido (max F2): {threshold:.2f}")

    print("\nTreino final e avaliacao no teste...")
    probas = {}
    for nome, modelo in modelos.items():
        modelo.fit(X_train, y_train)
        probas[nome] = modelo.predict_proba(X_test)[:, 1]

    resultados = [
        avaliar_teste("Regressao Logistica (baseline)",
                      probas["Regressao Logistica (baseline)"], y_test, 0.5),
        avaliar_teste("XGBoost", probas["XGBoost"], y_test, 0.5),
        avaliar_teste("XGBoost", probas["XGBoost"], y_test, threshold),
    ]
    for r in resultados:
        print({k: v for k, v in r.items() if k != "matriz_confusao"})

    xgb = modelos["XGBoost"]
    gerar_figuras(probas, y_test, threshold, xgb, list(X.columns))

    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(modelos["Regressao Logistica (baseline)"], MODELS_DIR / "logreg.joblib")
    xgb.save_model(MODELS_DIR / "xgb_model.json")
    (MODELS_DIR / "threshold.json").write_text(
        json.dumps({"threshold": threshold, "criterio": "max F2 (out-of-fold)"},
                   indent=2), encoding="utf-8")

    ranking = pd.DataFrame({
        "CustomerID": X_test.index,
        "prob_churn": probas["XGBoost"].round(4),
        "churn_real": y_test.values,
    }).sort_values("prob_churn", ascending=False)
    ranking["rank_risco"] = range(1, len(ranking) + 1)
    ranking.to_csv(SCORES_PATH, index=False)

    REPORT_PATH.write_text(
        gerar_relatorio(cv_tab, thr_tab, threshold, resultados,
                        len(X_train), len(X_test)), encoding="utf-8")
    print(f"\nRelatorio salvo em: {REPORT_PATH}")
    print(f"Ranking de risco salvo em: {SCORES_PATH}")


if __name__ == "__main__":
    main()
