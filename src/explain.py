"""Explicacoes SHAP do modelo de churn (Dia H, parte 1).

Calcula, para cada cliente do conjunto de teste, os 5 fatores que mais
empurram a previsao para cima (risco) ou para baixo, com rotulos legiveis
para a equipe de retencao. Tambem gera o resumo global (importancia media).

Saida: data/processed/shap_teste.json
  { "global": [{variavel, rotulo, impacto_medio}],
    "clientes": { "<CustomerID>": {"base": float, "fatores":
        [{variavel, rotulo, shap, valor}]} } }
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import shap
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from features import adicionar_features

BASE = Path(__file__).resolve().parents[1]
DATA_PATH = BASE / "data" / "processed" / "cell2cell_tratado.csv"
XGB_PATH = BASE / "models" / "xgb_model.json"
OUT_PATH = BASE / "data" / "processed" / "shap_teste.json"

SEED = 42
TOP_FATORES = 5

ROTULOS = {
    "CurrentEquipmentDays": "Dias com o aparelho atual",
    "IdadeAparelhoMeses": "Idade do aparelho (meses)",
    "MonthsInService": "Meses de contrato",
    "MonthlyMinutes": "Minutos mensais",
    "MonthlyRevenue": "Receita mensal",
    "TotalRecurringCharge": "Mensalidade recorrente",
    "PercChangeMinutes": "Variacao de minutos (%)",
    "PercChangeRevenues": "Variacao de receita (%)",
    "OverageMinutes": "Minutos excedentes",
    "RazaoOverage": "Proporcao de minutos excedentes",
    "ReceitaPorMinuto": "Receita por minuto (preco pago)",
    "ReceitaPorMes": "Receita media por mes de contrato",
    "DroppedCalls": "Chamadas caidas",
    "BlockedCalls": "Chamadas bloqueadas",
    "DroppedBlockedCalls": "Chamadas caidas + bloqueadas",
    "FalhasPorChamada": "Falhas por chamada (qualidade)",
    "NaoAtendidasPorChamada": "Nao atendidas por chamada",
    "UnansweredCalls": "Chamadas nao atendidas",
    "CustomerCareCalls": "Ligacoes ao atendimento",
    "CareCallsPorMes": "Ligacoes ao atendimento por mes",
    "RetentionCalls": "Ligacoes a equipe de retencao",
    "RetentionPorMes": "Ligacoes a retencao por mes",
    "MadeCallToRetentionTeam": "Ja ligou para a retencao",
    "RetentionOffersAccepted": "Ofertas de retencao aceitas",
    "HandsetPrice": "Preco do aparelho",
    "HandsetPriceKnown": "Preco do aparelho informado",
    "HandsetRefurbished": "Aparelho recondicionado",
    "HandsetWebCapable": "Aparelho com internet",
    "Handsets": "Qtde de aparelhos",
    "HandsetModels": "Qtde de modelos de aparelho",
    "RazaoAparelhoContrato": "Idade do aparelho vs contrato",
    "FimFidelizacao": "Fim do periodo de fidelizacao (11-16m)",
    "QuedaUso": "Queda recente de uso",
    "RazaoSubsAtivos": "Proporcao de linhas ativas",
    "UniqueSubs": "Linhas na conta",
    "ActiveSubs": "Linhas ativas",
    "ReceivedCalls": "Chamadas recebidas",
    "OutboundCalls": "Chamadas realizadas",
    "InboundCalls": "Chamadas de entrada",
    "PeakCallsInOut": "Chamadas em horario de pico",
    "OffPeakCallsInOut": "Chamadas fora de pico",
    "CallWaitingCalls": "Chamadas em espera",
    "ThreewayCalls": "Chamadas em conferencia",
    "DirectorAssistedCalls": "Chamadas com auxilio de telefonista",
    "RoamingCalls": "Chamadas em roaming",
    "CallForwardingCalls": "Chamadas encaminhadas",
    "CreditRating": "Nota de credito (1=melhor)",
    "AdjustmentsToCreditRating": "Ajustes na nota de credito",
    "IncomeGroup": "Faixa de renda",
    "AgeHH1": "Idade do titular",
    "AgeHH2": "Idade do 2o morador",
    "AgeHH1Known": "Idade do titular informada",
    "AgeHH2Known": "Idade do 2o morador informada",
    "ChildrenInHH": "Criancas em casa",
    "HomeownershipKnown": "Imovel proprio informado",
    "MissingBillingInfo": "Sem dados de fatura",
    "ServiceAreaFreq": "Porte da area de servico",
    "MonthsInService_x": "Meses de contrato",
    "NewCellphoneUser": "Usuario novo de celular",
    "NotNewCellphoneUser": "Usuario experiente de celular",
    "BuysViaMailOrder": "Compra por catalogo",
    "RespondsToMailOffers": "Responde a ofertas por correio",
    "OptOutMailings": "Recusou mala direta",
    "OwnsComputer": "Tem computador",
    "HasCreditCard": "Tem cartao de credito",
    "ReferralsMadeBySubscriber": "Indicacoes feitas",
}


def rotulo(variavel: str) -> str:
    if variavel in ROTULOS:
        return ROTULOS[variavel]
    for prefixo in ("MaritalStatus_", "PrizmCode_", "Occupation_"):
        if variavel.startswith(prefixo):
            return f"{prefixo[:-1]}: {variavel.split('_', 1)[1]}"
    return variavel


def main() -> None:
    df = pd.read_csv(DATA_PATH, index_col="CustomerID")
    X = adicionar_features(df.drop(columns=["Churn"]))
    y = df["Churn"]
    _, X_te, _, _ = train_test_split(X, y, test_size=0.2, stratify=y,
                                     random_state=SEED)

    modelo = XGBClassifier()
    modelo.load_model(XGB_PATH)

    explainer = shap.TreeExplainer(modelo)
    expl = explainer(X_te)
    valores = np.asarray(expl.values)
    base = float(np.ravel(expl.base_values)[0])
    colunas = list(X_te.columns)

    impacto_global = np.abs(valores).mean(axis=0)
    ordem_global = np.argsort(impacto_global)[::-1][:15]
    resumo_global = [{
        "variavel": colunas[i],
        "rotulo": rotulo(colunas[i]),
        "impacto_medio": round(float(impacto_global[i]), 4),
    } for i in ordem_global]

    clientes: dict[str, dict] = {}
    matriz_x = X_te.to_numpy()
    for pos, customer_id in enumerate(X_te.index):
        linha = valores[pos]
        ordem = np.argsort(np.abs(linha))[::-1][:TOP_FATORES]
        clientes[str(int(customer_id))] = {
            "base": round(base, 4),
            "fatores": [{
                "variavel": colunas[i],
                "rotulo": rotulo(colunas[i]),
                "shap": round(float(linha[i]), 4),
                "valor": round(float(matriz_x[pos, i]), 3),
            } for i in ordem],
        }

    OUT_PATH.write_text(
        json.dumps({"global": resumo_global, "clientes": clientes},
                   ensure_ascii=False),
        encoding="utf-8")
    print(f"SHAP calculado para {len(clientes):,} clientes de teste")
    print(f"Top 5 fatores globais: {[g['rotulo'] for g in resumo_global[:5]]}")
    print(f"Salvo em: {OUT_PATH} ({OUT_PATH.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
