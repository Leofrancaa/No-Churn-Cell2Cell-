"""Dashboard do Sistema Inteligente de Retencao - Cell2Cell.

Pagina atual: Engenheiro de IA (diagnostico do modulo de previsao).
A visao do Analista de Retencao (ranking, SHAP, acoes) chega no Dia H.

Rodar: streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve

BASE = Path(__file__).resolve().parents[1]
SCORES_PATH = BASE / "data" / "processed" / "scores_teste.csv"
THRESHOLD_PATH = BASE / "models" / "threshold.json"
XGB_PATH = BASE / "models" / "xgb_model.json"
REPORT_PATH = BASE / "reports" / "03_modulo_previsao.md"

st.set_page_config(page_title="Retencao Cell2Cell", page_icon="📡", layout="wide")


@st.cache_data
def carregar_scores() -> pd.DataFrame:
    return pd.read_csv(SCORES_PATH)


@st.cache_data
def carregar_threshold() -> float:
    return float(json.loads(THRESHOLD_PATH.read_text(encoding="utf-8"))["threshold"])


@st.cache_data
def carregar_importancias() -> pd.Series:
    from xgboost import XGBClassifier

    modelo = XGBClassifier()
    modelo.load_model(XGB_PATH)
    ganhos = modelo.get_booster().get_score(importance_type="gain")
    return pd.Series(ganhos).sort_values(ascending=False)


def figura_roc(df: pd.DataFrame) -> go.Figure:
    fpr, tpr, _ = roc_curve(df["churn_real"], df["prob_churn"])
    auc = roc_auc_score(df["churn_real"], df["prob_churn"])
    fig = go.Figure()
    fig.add_scatter(x=fpr, y=tpr, mode="lines", name=f"XGBoost (AUC={auc:.3f})")
    fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", name="Aleatorio",
                    line={"dash": "dash", "color": "gray"})
    fig.update_layout(title="Curva ROC - conjunto de teste",
                      xaxis_title="Taxa de falsos positivos",
                      yaxis_title="Recall", height=420)
    return fig


def figura_distribuicao(df: pd.DataFrame, threshold: float) -> go.Figure:
    fig = go.Figure()
    for valor, nome, cor in [(0, "Ficou", "#4c8cbf"), (1, "Cancelou", "#d9534f")]:
        fig.add_histogram(x=df.loc[df["churn_real"] == valor, "prob_churn"],
                          name=nome, opacity=0.65, marker_color=cor, nbinsx=50)
    fig.add_vline(x=threshold, line_dash="dash", line_color="black",
                  annotation_text=f"threshold {threshold:.2f}")
    fig.update_layout(barmode="overlay", title="Distribuicao do score de risco",
                      xaxis_title="Probabilidade prevista de churn", height=420)
    return fig


def figura_matriz(mc: np.ndarray) -> go.Figure:
    rotulos = ["Fica", "Cancela"]
    fig = go.Figure(go.Heatmap(
        z=mc, x=[f"Previsto: {r}" for r in rotulos],
        y=[f"Real: {r}" for r in rotulos],
        text=mc, texttemplate="%{text:,}", colorscale="Blues", showscale=False))
    fig.update_layout(title="Matriz de confusao", height=360)
    return fig


def pagina_engenheiro() -> None:
    st.header("🔧 Visao do Engenheiro de IA")
    st.caption("Diagnostico do modulo de previsao (XGBoost) no conjunto de "
               "teste - 20% dos dados, nunca vistos no treino.")

    df = carregar_scores()
    thr_oficial = carregar_threshold()

    st.subheader("Ponto de decisao")
    st.write("O threshold oficial foi escolhido maximizando **F2** nas "
             "predicoes out-of-fold do treino. Use o slider para explorar "
             "o trade-off em tempo real.")
    threshold = st.slider("Threshold de decisao", 0.05, 0.95, thr_oficial, 0.05,
                          help=f"Valor oficial em producao: {thr_oficial:.2f}")

    pred = (df["prob_churn"] >= threshold).astype(int)
    mc = confusion_matrix(df["churn_real"], pred)
    tn, fp, fn, tp = mc.ravel()
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    precisao = tp / (tp + fp) if (tp + fp) else 0.0
    auc = roc_auc_score(df["churn_real"], df["prob_churn"])

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("AUC-ROC", f"{auc:.3f}", help="Nao depende do threshold")
    col2.metric("Recall (deteccao)", f"{recall:.1%}",
                delta=f"{recall - 0.575:+.1%} vs thr 0,50")
    col3.metric("Precisao", f"{precisao:.1%}")
    col4.metric("Cancelamentos perdidos (FN)", f"{fn:,}")
    col5.metric("Promocoes 'desperdicadas' (FP)", f"{fp:,}")

    st.info(f"**Leitura de negocio:** com threshold {threshold:.2f}, a equipe "
            f"abordaria **{tp + fp:,} clientes** e capturaria **{recall:.0%}** "
            f"de todos os que cancelariam ({tp:,} de {tp + fn:,}). "
            "Falso positivo custa uma promocao; falso negativo custa o cliente.")

    esq, dir_ = st.columns(2)
    esq.plotly_chart(figura_matriz(mc), width="stretch")
    dir_.plotly_chart(figura_roc(df), width="stretch")

    st.plotly_chart(figura_distribuicao(df, threshold), width="stretch")

    st.subheader("Variaveis mais importantes (ganho no XGBoost)")
    importancias = carregar_importancias().head(20).iloc[::-1]
    fig = go.Figure(go.Bar(x=importancias.values, y=importancias.index,
                           orientation="h", marker_color="#4c8cbf"))
    fig.update_layout(height=520, margin={"l": 10})
    st.plotly_chart(fig, width="stretch")

    st.subheader("Topo do ranking de risco")
    st.dataframe(df.head(25), width="stretch", hide_index=True)

    with st.expander("Relatorio completo do Dia N"):
        st.markdown(REPORT_PATH.read_text(encoding="utf-8"))


def pagina_analista() -> None:
    st.header("📋 Visao do Analista de Retencao")
    st.info("Em construcao (Dia H): ranking de risco com explicacao SHAP "
            "individual, acao de retencao recomendada pelo agente e modo "
            "simulacao com curvas de aprendizado.")


def main() -> None:
    st.title("📡 Sistema Inteligente de Retencao - Cell2Cell")
    aba_eng, aba_analista = st.tabs(["Engenheiro de IA", "Analista de Retencao"])
    with aba_eng:
        pagina_engenheiro()
    with aba_analista:
        pagina_analista()


if __name__ == "__main__":
    main()
