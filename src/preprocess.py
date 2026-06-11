"""Pipeline de tratamento do dataset Cell2Cell.

Cada transformacao e registrada em um log de acoes que alimenta o
diagnostico de validacao (reports/02_diagnostico_tratamento.md).

Os parametros aprendidos (medianas, frequencias) sao salvos em
data/processed/preprocess_params.json para que dados novos recebam
exatamente o mesmo tratamento na fase de teste.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW_PATH = BASE / "data" / "raw" / "cell2celltrain.csv"
OUT_PATH = BASE / "data" / "processed" / "cell2cell_tratado.csv"
PARAMS_PATH = BASE / "data" / "processed" / "preprocess_params.json"
REPORT_PATH = BASE / "reports" / "02_diagnostico_tratamento.md"

# Colunas binarias Yes/No (alvo tratado a parte)
COLS_YES_NO = [
    "ChildrenInHH", "HandsetRefurbished", "HandsetWebCapable", "TruckOwner",
    "RVOwner", "BuysViaMailOrder", "RespondsToMailOffers", "OptOutMailings",
    "NonUSTravel", "OwnsComputer", "HasCreditCard", "NewCellphoneUser",
    "NotNewCellphoneUser", "OwnsMotorcycle", "MadeCallToRetentionTeam",
]

# Bloco de uso/fatura: as mesmas 156 linhas tem NaN em todas elas
COLS_FATURA = [
    "MonthlyRevenue", "MonthlyMinutes", "TotalRecurringCharge",
    "DirectorAssistedCalls", "OverageMinutes", "RoamingCalls",
]

ORDEM_CREDITO = {
    "1-Highest": 1, "2-High": 2, "3-Good": 3, "4-Medium": 4,
    "5-Low": 5, "6-VeryLow": 6, "7-Lowest": 7,
}


def tratar(df: pd.DataFrame) -> tuple[pd.DataFrame, dict, list[dict]]:
    """Aplica o tratamento e retorna (df_tratado, params, log_de_acoes)."""
    log: list[dict] = []
    params: dict = {"medianas": {}, "freq_service_area": {}}
    out = df.copy()

    def registra(coluna: str, acao: str, afetados: int, motivo: str) -> None:
        log.append({
            "coluna": coluna, "acao": acao,
            "linhas_afetadas": int(afetados), "motivo": motivo,
        })

    # --- 1. Alvo ---
    out["Churn"] = (out["Churn"] == "Yes").astype(int)
    registra("Churn", "Mapeado Yes/No -> 1/0", len(out),
             "Alvo binario exigido pelos modelos")

    # --- 2. Binarias Yes/No ---
    for col in COLS_YES_NO:
        out[col] = (out[col] == "Yes").astype(int)
    registra(", ".join(COLS_YES_NO), "Mapeadas Yes/No -> 1/0", len(out),
             "15 colunas binarias; evita one-hot desnecessario")

    # --- 3. Faltantes disfarcados: Homeownership e MaritalStatus ---
    out["HomeownershipKnown"] = (out["Homeownership"] == "Known").astype(int)
    n_unk = int((df["Homeownership"] == "Unknown").sum())
    out = out.drop(columns=["Homeownership"])
    registra("Homeownership", "Convertida em flag HomeownershipKnown (1/0)", n_unk,
             "33% 'Unknown'; a coluna so informa se o dado existe, nao o valor")

    n_unk = int((df["MaritalStatus"] == "Unknown").sum())
    dummies = pd.get_dummies(out["MaritalStatus"], prefix="MaritalStatus", dtype=int)
    out = pd.concat([out.drop(columns=["MaritalStatus"]), dummies], axis=1)
    registra("MaritalStatus", "One-hot (Yes/No/Unknown como 3 colunas)", n_unk,
             "39% 'Unknown' e informacao demais para descartar; "
             "'Unknown' vira categoria propria")

    # --- 4. HandsetPrice: texto -> numerico + flag ---
    n_unk = int((df["HandsetPrice"] == "Unknown").sum())
    preco = pd.to_numeric(out["HandsetPrice"].replace("Unknown", np.nan), errors="coerce")
    out["HandsetPriceKnown"] = preco.notna().astype(int)
    mediana = float(preco.median())
    params["medianas"]["HandsetPrice"] = mediana
    out["HandsetPrice"] = preco.fillna(mediana)
    registra("HandsetPrice", f"'Unknown'->NaN, flag de conhecido, imputada mediana ({mediana})",
             n_unk, "57% 'Unknown'; flag preserva o padrao de ausencia, mediana evita "
             "distorcer a escala")

    # --- 5. AgeHH1/AgeHH2: zero significa idade desconhecida ---
    for col in ["AgeHH1", "AgeHH2"]:
        zeros = int((df[col] == 0).sum())
        nans = int(df[col].isna().sum())
        idade = out[col].replace(0, np.nan)
        out[f"{col}Known"] = idade.notna().astype(int)
        mediana = float(idade.median())
        params["medianas"][col] = mediana
        out[col] = idade.fillna(mediana)
        registra(col, f"0->NaN, flag de conhecido, imputada mediana ({mediana})",
                 zeros + nans, "Idade 0 nao existe; zero codifica 'nao informado'")

    # --- 6. CurrentEquipmentDays: negativos impossiveis ---
    negativos = int((df["CurrentEquipmentDays"] < 0).sum())
    dias = out["CurrentEquipmentDays"].where(out["CurrentEquipmentDays"] >= 0)
    mediana = float(dias.median())
    params["medianas"]["CurrentEquipmentDays"] = mediana
    out["CurrentEquipmentDays"] = dias.fillna(mediana)
    registra("CurrentEquipmentDays", f"Negativos->NaN, imputada mediana ({mediana})",
             negativos + int(df["CurrentEquipmentDays"].isna().sum()),
             "Dias de uso do aparelho nao podem ser negativos (erro de registro)")

    # --- 7. Bloco de fatura: 156 linhas sem nenhum dado de uso ---
    sem_fatura = out[COLS_FATURA].isna().all(axis=1)
    out["MissingBillingInfo"] = sem_fatura.astype(int)
    for col in COLS_FATURA:
        mediana = float(out[col].median())
        params["medianas"][col] = mediana
        out[col] = out[col].fillna(mediana)
    registra(", ".join(COLS_FATURA),
             "Flag MissingBillingInfo + imputacao por mediana", int(sem_fatura.sum()),
             "As mesmas 156 linhas (0,31%) nao tem nenhum dado de fatura; "
             "a flag preserva essa informacao")

    # --- 8. Demais numericas com NaN residual ---
    residuais = ["PercChangeMinutes", "PercChangeRevenues", "Handsets",
                 "HandsetModels"]
    for col in residuais:
        nans = int(out[col].isna().sum())
        if nans:
            mediana = float(out[col].median())
            params["medianas"][col] = mediana
            out[col] = out[col].fillna(mediana)
            registra(col, f"Imputada mediana ({mediana})", nans,
                     "NaN residual (<1%); mediana e robusta a outliers")

    # --- 9. CreditRating ordinal ---
    out["CreditRating"] = out["CreditRating"].map(ORDEM_CREDITO).astype(int)
    registra("CreditRating", "Mapeado para escala ordinal 1-7", len(out),
             "Categorias tem ordem natural (1-Highest ... 7-Lowest)")

    # --- 10. PrizmCode e Occupation: one-hot ---
    for col in ["PrizmCode", "Occupation"]:
        dummies = pd.get_dummies(out[col], prefix=col, dtype=int)
        out = pd.concat([out.drop(columns=[col]), dummies], axis=1)
        registra(col, f"One-hot ({dummies.shape[1]} colunas)", len(out),
                 "Baixa cardinalidade e sem ordem natural")

    # --- 11. ServiceArea: alta cardinalidade -> frequency encoding ---
    n_missing = int(df["ServiceArea"].isna().sum())
    area = out["ServiceArea"].fillna("DESCONHECIDA")
    freq = area.value_counts(normalize=True)
    params["freq_service_area"] = freq.round(6).to_dict()
    out["ServiceAreaFreq"] = area.map(freq)
    out = out.drop(columns=["ServiceArea"])
    registra("ServiceArea", "Frequency encoding (proporcao de clientes na area)",
             n_missing, "747 categorias inviabilizam one-hot; frequencia captura "
             "porte da area sem usar o alvo (sem vazamento)")

    # --- 12. CustomerID sai das features ---
    out = out.set_index("CustomerID")
    registra("CustomerID", "Movido para indice (fora das features)", len(out),
             "Identificador nao tem valor preditivo; mantido para rastrear clientes")

    return out, params, log


def gerar_diagnostico(df_raw: pd.DataFrame, df_out: pd.DataFrame,
                      log: list[dict]) -> str:
    linhas = [
        "# Diagnostico do Tratamento de Dados - Cell2Cell",
        "",
        f"- Dataset bruto: **{df_raw.shape[0]:,} linhas x {df_raw.shape[1]} colunas**",
        f"- Dataset tratado: **{df_out.shape[0]:,} linhas x {df_out.shape[1]} colunas** "
        "(nenhuma linha removida)",
        f"- NaN restantes: **{int(df_out.isna().sum().sum())}**",
        f"- Colunas nao numericas restantes: "
        f"**{int((~df_out.dtypes.apply(pd.api.types.is_numeric_dtype)).sum())}**",
        f"- Alvo: Churn = 1 em **{df_out['Churn'].mean():.2%}** dos clientes "
        "(desbalanceamento moderado - sera tratado no treinamento, nao aqui)",
        "",
        "## Acoes aplicadas",
        "",
        "| Coluna(s) | Acao | Linhas afetadas | Motivo |",
        "|---|---|---:|---|",
    ]
    for item in log:
        linhas.append(
            f"| {item['coluna']} | {item['acao']} | "
            f"{item['linhas_afetadas']:,} | {item['motivo']} |"
        )
    linhas += [
        "",
        "## Decisoes que ficaram para a fase de treinamento (de proposito)",
        "",
        "- **Desbalanceamento de classes**: SMOTE/class_weight serao aplicados "
        "dentro da validacao cruzada para nao vazar informacao entre folds.",
        "- **Outliers**: nao foram cortados. XGBoost (arvores) e robusto a "
        "outliers; cortar agora destruiria sinal real de uso extremo.",
        "- **Escalonamento**: apenas a Regressao Logistica precisa; o "
        "StandardScaler entrara no pipeline dela, ajustado so no treino.",
        "",
        "## Validacao sugerida",
        "",
        "1. Conferir que nenhuma linha foi perdida (contagem acima).",
        "2. Conferir que nao restam NaN nem colunas de texto.",
        "3. Conferir as medianas usadas em `preprocess_params.json`.",
        "4. Conferir que a taxa de churn nao mudou apos o tratamento.",
    ]
    return "\n".join(linhas)


def main() -> None:
    df_raw = pd.read_csv(RAW_PATH)
    df_out, params, log = tratar(df_raw)

    assert df_out.isna().sum().sum() == 0, "Restaram NaN apos o tratamento"
    assert df_out.dtypes.apply(pd.api.types.is_numeric_dtype).all(), \
        "Restaram colunas nao numericas"
    assert len(df_out) == len(df_raw), "Linhas foram perdidas no tratamento"

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(OUT_PATH)
    PARAMS_PATH.write_text(json.dumps(params, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(gerar_diagnostico(df_raw, df_out, log), encoding="utf-8")

    print(f"Tratado: {df_out.shape[0]:,} linhas x {df_out.shape[1]} colunas")
    print(f"Dataset salvo em:    {OUT_PATH}")
    print(f"Parametros salvos:   {PARAMS_PATH}")
    print(f"Diagnostico salvo:   {REPORT_PATH}")


if __name__ == "__main__":
    main()
