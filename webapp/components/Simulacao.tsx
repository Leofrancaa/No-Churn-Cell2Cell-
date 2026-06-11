"use client";

import type { Retencao } from "@/lib/types";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
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

function CardPolitica({
  segmento,
  retencao,
}: {
  segmento: string;
  retencao: Retencao;
}) {
  const linhas = retencao.politica[segmento];
  const nomeAcao = Object.fromEntries(
    retencao.acoes.map((a) => [a.id, a.nome]),
  );
  const custoAcao = Object.fromEntries(
    retencao.acoes.map((a) => [a.id, a.custo]),
  );
  const clientes = retencao.distribuicao_segmentos[segmento] ?? 0;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-baseline justify-between">
        <h4 className="font-medium text-sky-300">{segmento}</h4>
        <span className="text-xs text-slate-500">
          {clientes.toLocaleString("pt-BR")} clientes
        </span>
      </div>
      <div className="mt-3 space-y-2">
        {linhas.map((linha, indice) => (
          <div key={linha.acao} className="text-xs">
            <div className="flex items-center justify-between">
              <span
                className={
                  indice === 0 ? "font-medium text-emerald-300" : "text-slate-400"
                }
              >
                {indice === 0 && "✓ "}
                {nomeAcao[linha.acao]}
              </span>
              <span className="text-slate-500">
                {(linha.taxa_estimada * 100).toFixed(0)}% · R${" "}
                {custoAcao[linha.acao]}
              </span>
            </div>
            <div className="mt-1 h-1.5 rounded bg-slate-800">
              <div
                className={`h-1.5 rounded ${
                  indice === 0 ? "bg-emerald-500" : "bg-slate-600"
                }`}
                style={{ width: `${linha.taxa_estimada * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Simulacao({ retencao }: { retencao: Retencao }) {
  const taxaFinal = retencao.curva[retencao.curva.length - 1]?.taxa_aceite ?? 0;

  return (
    <section className="mt-6">
      <h2 className="text-lg font-medium text-slate-100">
        Modo simulação — como o agente aprendeu
      </h2>
      <p className="mt-1 text-sm text-slate-400">
        O agente (Thompson Sampling) sugeriu ofertas para{" "}
        {retencao.rodadas.toLocaleString("pt-BR")} clientes simulados, observou
        aceite/recusa e aprendeu a melhor ação por perfil — sem nunca ver as
        taxas reais. Taxa de aceitação final:{" "}
        <span className="font-semibold text-emerald-400">
          {(taxaFinal * 100).toFixed(1)}%
        </span>
        .
      </p>

      <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-5">
        <h3 className="mb-3 font-medium text-slate-200">
          Curva de aprendizado
        </h3>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={retencao.curva}>
            <CartesianGrid stroke="#1e293b" />
            <XAxis
              dataKey="rodada"
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              label={{
                value: "ofertas feitas",
                position: "insideBottom",
                offset: -2,
                fill: "#64748b",
                fontSize: 11,
              }}
            />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <Tooltip contentStyle={ESTILO_TOOLTIP} />
            <Legend />
            <Line
              dataKey="taxa_aceite"
              name="Taxa de aceitação (janela)"
              stroke="#34d399"
              dot={false}
              strokeWidth={2}
            />
            <Line
              dataKey="regret_medio"
              name="Arrependimento médio"
              stroke="#f87171"
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
        <p className="mt-2 text-xs text-slate-500">
          A taxa de aceitação sobe e o arrependimento (diferença para a ação
          ótima) cai — o agente converge para a melhor oferta de cada perfil.
        </p>
      </div>

      <h3 className="mt-5 font-medium text-slate-200">
        Política aprendida por perfil
      </h3>
      <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {retencao.segmentos.map((segmento) => (
          <CardPolitica
            key={segmento}
            segmento={segmento}
            retencao={retencao}
          />
        ))}
      </div>
    </section>
  );
}
