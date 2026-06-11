"""Exploração inicial do dataset Cell2Cell.

Gera um perfil completo do dataset bruto: tipos, valores faltantes,
cardinalidade das categóricas, estatísticas das numéricas, balanceamento
do alvo e possíveis problemas de qualidade (duplicatas, valores suspeitos).

Saída: reports/01_perfil_dataset_bruto.txt
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd

RAW_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "cell2celltrain.csv"
REPORT_PATH = Path(__file__).resolve().parents[1] / "reports" / "01_perfil_dataset_bruto.txt"


def secao(buf: io.StringIO, titulo: str) -> None:
    buf.write(f"\n{'=' * 80}\n{titulo}\n{'=' * 80}\n")


def main() -> None:
    df = pd.read_csv(RAW_PATH)
    buf = io.StringIO()

    secao(buf, "1. DIMENSOES E TIPOS")
    buf.write(f"Linhas: {len(df):,} | Colunas: {df.shape[1]}\n")
    buf.write(f"Memoria: {df.memory_usage(deep=True).sum() / 1e6:.1f} MB\n\n")
    tipos = df.dtypes.value_counts()
    buf.write(f"Distribuicao de tipos:\n{tipos.to_string()}\n")

    secao(buf, "2. ALVO (Churn)")
    contagem = df["Churn"].value_counts(dropna=False)
    proporcao = df["Churn"].value_counts(normalize=True, dropna=False)
    buf.write(pd.DataFrame({"contagem": contagem, "proporcao": proporcao.round(4)}).to_string())
    buf.write("\n")

    secao(buf, "3. VALORES FALTANTES")
    faltantes = df.isna().sum()
    faltantes = faltantes[faltantes > 0].sort_values(ascending=False)
    if faltantes.empty:
        buf.write("Nenhuma coluna com NaN explicito.\n")
    else:
        tabela = pd.DataFrame(
            {"qtd_nan": faltantes, "pct": (faltantes / len(df) * 100).round(2)}
        )
        buf.write(tabela.to_string())
        buf.write("\n")

    secao(buf, "4. VALORES 'FALTANTES DISFARCADOS' EM CATEGORICAS")
    cat_cols = df.select_dtypes(include="object").columns
    suspeitos = ("unknown", "known", "na", "n/a", "none", "?", "")
    for col in cat_cols:
        valores = df[col].astype(str).str.strip().str.lower()
        achados = valores[valores.isin(suspeitos)].value_counts()
        if not achados.empty:
            buf.write(f"{col}: {achados.to_dict()}\n")

    secao(buf, "5. CARDINALIDADE DAS CATEGORICAS")
    card = df[cat_cols].nunique().sort_values(ascending=False)
    buf.write(card.to_string())
    buf.write("\n\nValores unicos (colunas com ate 12 categorias):\n")
    for col in cat_cols:
        if df[col].nunique() <= 12:
            buf.write(f"  {col}: {sorted(df[col].dropna().unique().tolist())}\n")

    secao(buf, "6. ESTATISTICAS DAS NUMERICAS")
    num_cols = df.select_dtypes(include=np.number).columns
    buf.write(df[num_cols].describe().T.round(2).to_string())
    buf.write("\n")

    secao(buf, "7. PROBLEMAS DE QUALIDADE")
    buf.write(f"CustomerID duplicados: {df['CustomerID'].duplicated().sum()}\n")
    buf.write(f"Linhas inteiras duplicadas: {df.duplicated().sum()}\n\n")
    negativas_ok = {"PercChangeMinutes", "PercChangeRevenues"}
    for col in num_cols:
        qtd_neg = int((df[col] < 0).sum())
        if qtd_neg > 0 and col not in negativas_ok:
            buf.write(f"Valores negativos suspeitos em {col}: {qtd_neg}\n")
    if "HandsetPrice" in cat_cols:
        buf.write(
            f"\nHandsetPrice e texto; valores: "
            f"{df['HandsetPrice'].value_counts(dropna=False).head(15).to_dict()}\n"
        )

    secao(buf, "8. TAXA DE CHURN POR FAIXA (variaveis-chave)")
    df["_churn_bin"] = (df["Churn"] == "Yes").astype(int)
    chave = ["MonthsInService", "MonthlyRevenue", "CurrentEquipmentDays", "RetentionCalls"]
    for col in chave:
        serie = pd.to_numeric(df[col], errors="coerce")
        faixas = pd.qcut(serie, q=4, duplicates="drop")
        taxa = df.groupby(faixas, observed=True)["_churn_bin"].agg(["mean", "count"]).round(3)
        buf.write(f"\n--- {col} ---\n{taxa.to_string()}\n")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(buf.getvalue(), encoding="utf-8")
    print(buf.getvalue())
    print(f"\nRelatorio salvo em: {REPORT_PATH}")


if __name__ == "__main__":
    main()
