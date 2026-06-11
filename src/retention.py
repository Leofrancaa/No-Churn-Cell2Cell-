"""Modulo de retencao (Dia H, parte 2): simulador + agente de recomendacao.

Componentes:
  1. Segmentacao interpretavel dos clientes de teste em 5 perfis de risco
     (regras sobre as features derivadas, com cortes por quantil).
  2. Simulador de aceitacao: matriz OCULTA de probabilidade de aceite por
     (segmento, acao) - faz o papel do cliente real respondendo a oferta.
  3. Agente Thompson Sampling (bandit Beta-Bernoulli por segmento): sugere
     uma acao, observa aceite/recusa do simulador e melhora com o tempo.
     O agente NUNCA ve a matriz oculta - aprende so pelo feedback.

Saida: data/processed/retencao.json (politica aprendida, curvas de
aprendizado, segmento e acao recomendada por cliente do teste).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from features import adicionar_features

BASE = Path(__file__).resolve().parents[1]
DATA_PATH = BASE / "data" / "processed" / "cell2cell_tratado.csv"
SCORES_PATH = BASE / "data" / "processed" / "scores_teste.csv"
OUT_PATH = BASE / "data" / "processed" / "retencao.json"

SEED = 42
RODADAS = 8000
JANELA_CURVA = 400

ACOES = [
    {"id": "desconto", "nome": "Desconto na mensalidade", "custo": 30},
    {"id": "upgrade", "nome": "Upgrade de aparelho subsidiado", "custo": 80},
    {"id": "suporte", "nome": "Ligacao proativa do suporte", "custo": 8},
    {"id": "bonus", "nome": "Pacote de minutos bonus", "custo": 15},
]

# Matriz oculta do simulador: P(aceitar | segmento, acao).
# Plausivel de negocio: a acao que ataca a dor do segmento converte mais.
VERDADE_OCULTA = {
    "Insatisfeito com o servico": {"desconto": 0.30, "upgrade": 0.22,
                                   "suporte": 0.52, "bonus": 0.26},
    "Sensivel a preco": {"desconto": 0.55, "upgrade": 0.25,
                         "suporte": 0.18, "bonus": 0.38},
    "Aparelho desatualizado": {"desconto": 0.32, "upgrade": 0.58,
                               "suporte": 0.16, "bonus": 0.22},
    "Fim de fidelizacao": {"desconto": 0.45, "upgrade": 0.40,
                           "suporte": 0.20, "bonus": 0.28},
    "Perfil geral": {"desconto": 0.28, "upgrade": 0.24,
                     "suporte": 0.22, "bonus": 0.30},
}
SEGMENTOS = list(VERDADE_OCULTA)


def segmentar(X: pd.DataFrame) -> tuple[pd.Series, dict]:
    """Atribui um segmento por cliente (primeira regra que casar vence)."""
    cortes = {
        "falhas_q75": float(X["FalhasPorChamada"].quantile(0.75)),
        "care_q75": float(X["CareCallsPorMes"].quantile(0.75)),
        "overage_q75": float(X["RazaoOverage"].quantile(0.75)),
        "preco_min_q75": float(X["ReceitaPorMinuto"].quantile(0.75)),
        "aparelho_meses": 12.0,
    }
    insatisfeito = (X["FalhasPorChamada"] >= cortes["falhas_q75"]) | (
        X["CareCallsPorMes"] >= cortes["care_q75"])
    sensivel = (X["RazaoOverage"] >= cortes["overage_q75"]) | (
        X["ReceitaPorMinuto"] >= cortes["preco_min_q75"])
    aparelho = X["IdadeAparelhoMeses"] >= cortes["aparelho_meses"]
    fidelizacao = X["FimFidelizacao"] == 1

    segmento = pd.Series("Perfil geral", index=X.index)
    segmento[fidelizacao] = "Fim de fidelizacao"
    segmento[aparelho] = "Aparelho desatualizado"
    segmento[sensivel] = "Sensivel a preco"
    segmento[insatisfeito] = "Insatisfeito com o servico"
    return segmento, cortes


def simular_agente(segmentos_clientes: pd.Series,
                   rng: np.random.Generator) -> tuple[dict, list]:
    """Thompson Sampling: um par Beta(sucessos+1, falhas+1) por (seg, acao)."""
    ids_acoes = [a["id"] for a in ACOES]
    sucessos = {s: {a: 0 for a in ids_acoes} for s in SEGMENTOS}
    falhas = {s: {a: 0 for a in ids_acoes} for s in SEGMENTOS}
    melhor_taxa = {s: max(VERDADE_OCULTA[s].values()) for s in SEGMENTOS}

    populacao = segmentos_clientes.to_numpy()
    aceites_janela: list[int] = []
    regret_acumulado = 0.0
    curva = []

    for t in range(1, RODADAS + 1):
        segmento = populacao[rng.integers(len(populacao))]
        amostras = {a: rng.beta(sucessos[segmento][a] + 1,
                                falhas[segmento][a] + 1) for a in ids_acoes}
        acao = max(amostras, key=lambda a: amostras[a])
        aceitou = int(rng.random() < VERDADE_OCULTA[segmento][acao])
        if aceitou:
            sucessos[segmento][acao] += 1
        else:
            falhas[segmento][acao] += 1

        regret_acumulado += melhor_taxa[segmento] - VERDADE_OCULTA[segmento][acao]
        aceites_janela.append(aceitou)
        if len(aceites_janela) > JANELA_CURVA:
            aceites_janela.pop(0)
        if t % 50 == 0:
            curva.append({
                "rodada": t,
                "taxa_aceite": round(float(np.mean(aceites_janela)), 4),
                "regret_medio": round(regret_acumulado / t, 4),
            })

    politica = {}
    for s in SEGMENTOS:
        linhas = []
        for a in ids_acoes:
            tentativas = sucessos[s][a] + falhas[s][a]
            taxa = sucessos[s][a] / tentativas if tentativas else 0.0
            linhas.append({"acao": a, "tentativas": tentativas,
                           "aceites": sucessos[s][a],
                           "taxa_estimada": round(taxa, 4),
                           "taxa_real_oculta": VERDADE_OCULTA[s][a]})
        linhas.sort(key=lambda r: r["taxa_estimada"], reverse=True)
        politica[s] = linhas
    return politica, curva


def main() -> None:
    df = pd.read_csv(DATA_PATH, index_col="CustomerID")
    X = adicionar_features(df.drop(columns=["Churn"]))
    y = df["Churn"]
    _, X_te, _, _ = train_test_split(X, y, test_size=0.2, stratify=y,
                                     random_state=SEED)

    segmentos_clientes, cortes = segmentar(X_te)
    print("Distribuicao de segmentos no teste:")
    print(segmentos_clientes.value_counts().to_string())

    rng = np.random.default_rng(SEED)
    politica, curva = simular_agente(segmentos_clientes, rng)

    melhor_acao = {s: politica[s][0]["acao"] for s in SEGMENTOS}
    acertou_oracle = {
        s: melhor_acao[s] == max(VERDADE_OCULTA[s], key=VERDADE_OCULTA[s].get)
        for s in SEGMENTOS
    }
    print(f"\nMelhor acao aprendida por segmento: {melhor_acao}")
    print(f"Agente encontrou a acao otima? {acertou_oracle}")
    print(f"Taxa de aceite final (janela): {curva[-1]['taxa_aceite']:.1%}")

    nome_acao = {a["id"]: a["nome"] for a in ACOES}
    clientes = {
        str(int(cid)): {
            "segmento": seg,
            "acao": melhor_acao[seg],
            "acao_nome": nome_acao[melhor_acao[seg]],
            "taxa_esperada": politica[seg][0]["taxa_estimada"],
        }
        for cid, seg in segmentos_clientes.items()
    }

    OUT_PATH.write_text(json.dumps({
        "acoes": ACOES,
        "segmentos": SEGMENTOS,
        "cortes_segmentacao": cortes,
        "distribuicao_segmentos": segmentos_clientes.value_counts().to_dict(),
        "politica": politica,
        "melhor_acao": melhor_acao,
        "curva": curva,
        "rodadas": RODADAS,
        "clientes": clientes,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"\nSalvo em: {OUT_PATH} ({OUT_PATH.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
