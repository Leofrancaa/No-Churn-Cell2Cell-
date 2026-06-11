"""Features derivadas para o modelo de churn.

Todas sao razoes/combinacoes calculadas linha a linha sobre o dataset ja
tratado - nao aprendem nada do conjunto (sem medianas, sem alvo), entao
podem ser aplicadas identicamente a dados novos na inferencia.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def adicionar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna uma copia de df com as features derivadas anexadas."""
    out = df.copy()

    minutos = out["MonthlyMinutes"].clip(lower=1)
    meses = out["MonthsInService"].clip(lower=1)
    chamadas_total = (
        out["OutboundCalls"] + out["InboundCalls"] + out["ReceivedCalls"]
    ).clip(lower=1)

    # Valor e consumo
    out["ReceitaPorMinuto"] = out["MonthlyRevenue"] / minutos
    out["RazaoOverage"] = out["OverageMinutes"] / minutos
    out["ReceitaPorMes"] = out["MonthlyRevenue"] / meses

    # Qualidade do servico (atrito tecnico)
    out["FalhasPorChamada"] = out["DroppedBlockedCalls"] / chamadas_total
    out["NaoAtendidasPorChamada"] = out["UnansweredCalls"] / chamadas_total

    # Atrito com atendimento
    out["CareCallsPorMes"] = out["CustomerCareCalls"] / meses
    out["RetentionPorMes"] = out["RetentionCalls"] / meses

    # Ciclo de vida do aparelho e do contrato
    out["IdadeAparelhoMeses"] = out["CurrentEquipmentDays"] / 30.0
    out["RazaoAparelhoContrato"] = out["IdadeAparelhoMeses"] / meses
    out["FimFidelizacao"] = (
        (out["MonthsInService"] >= 11) & (out["MonthsInService"] <= 16)
    ).astype(int)

    # Engajamento da conta
    out["RazaoSubsAtivos"] = out["ActiveSubs"] / out["UniqueSubs"].clip(lower=1)
    out["QuedaUso"] = (out["PercChangeMinutes"] < 0).astype(int) * np.abs(
        out["PercChangeMinutes"]
    )

    return out
