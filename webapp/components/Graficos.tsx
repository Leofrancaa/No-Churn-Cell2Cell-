"use client";

import type {
  FaixaDistribuicao,
  Importancia,
  PontoRoc,
} from "@/lib/types";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const ESTILO_TOOLTIP = {
  backgroundColor: "#0f172a",
  border: "1px solid #334155",
  borderRadius: 8,
  color: "#e2e8f0",
} as const;

export function GraficoRoc({ roc, auc }: { roc: PontoRoc[]; auc: number }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <h3 className="mb-3 font-medium text-slate-200">
        Curva ROC — teste (AUC {auc.toFixed(3)})
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={roc}>
          <CartesianGrid stroke="#1e293b" />
          <XAxis
            dataKey="fpr"
            type="number"
            domain={[0, 1]}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            label={{
              value: "Falsos positivos",
              position: "insideBottom",
              offset: -2,
              fill: "#64748b",
              fontSize: 11,
            }}
          />
          <YAxis
            domain={[0, 1]}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            label={{
              value: "Recall",
              angle: -90,
              position: "insideLeft",
              fill: "#64748b",
              fontSize: 11,
            }}
          />
          <Tooltip contentStyle={ESTILO_TOOLTIP} />
          <Line
            dataKey="tpr"
            stroke="#38bdf8"
            dot={false}
            strokeWidth={2}
            name="XGBoost"
          />
          <Line
            dataKey="fpr"
            stroke="#475569"
            dot={false}
            strokeDasharray="5 5"
            name="Aleatório"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function GraficoDistribuicao({
  distribuicao,
  threshold,
}: {
  distribuicao: FaixaDistribuicao[];
  threshold: number;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <h3 className="mb-3 font-medium text-slate-200">
        Distribuição do score de risco
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={distribuicao} barCategoryGap={0}>
          <CartesianGrid stroke="#1e293b" />
          <XAxis
            dataKey="score"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickFormatter={(v: number) => v.toFixed(1)}
          />
          <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
          <Tooltip contentStyle={ESTILO_TOOLTIP} />
          <Legend />
          <Bar dataKey="ficou" name="Ficou" fill="#38bdf8" opacity={0.7} />
          <Bar dataKey="cancelou" name="Cancelou" fill="#f87171" opacity={0.7} />
          <ReferenceLine
            x={distribuicao.reduce(
              (maisProximo, faixa) =>
                Math.abs(faixa.score - threshold) <
                Math.abs(maisProximo - threshold)
                  ? faixa.score
                  : maisProximo,
              distribuicao[0]?.score ?? 0,
            )}
            stroke="#facc15"
            strokeDasharray="4 4"
            label={{
              value: `threshold ${threshold.toFixed(2)}`,
              fill: "#facc15",
              fontSize: 11,
            }}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function GraficoImportancias({
  importancias,
}: {
  importancias: Importancia[];
}) {
  const dados = [...importancias].reverse();
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <h3 className="mb-3 font-medium text-slate-200">
        Variáveis mais importantes (ganho no XGBoost)
      </h3>
      <ResponsiveContainer width="100%" height={480}>
        <BarChart data={dados} layout="vertical" margin={{ left: 60 }}>
          <CartesianGrid stroke="#1e293b" />
          <XAxis type="number" tick={{ fill: "#94a3b8", fontSize: 11 }} />
          <YAxis
            dataKey="variavel"
            type="category"
            width={150}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
          />
          <Tooltip contentStyle={ESTILO_TOOLTIP} />
          <Bar dataKey="ganho" name="Ganho" fill="#38bdf8" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
