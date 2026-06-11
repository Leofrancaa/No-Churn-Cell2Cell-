"use client";

import type { Acao, ClienteDetalhe } from "@/lib/types";

interface PainelClienteProps {
  cliente: ClienteDetalhe | null;
  acoes: Acao[];
  carregando: boolean;
}

function BarraFator({
  rotulo,
  shap,
  valor,
  maxAbs,
}: {
  rotulo: string;
  shap: number;
  valor: number;
  maxAbs: number;
}) {
  const largura = Math.max(6, (Math.abs(shap) / maxAbs) * 100);
  const aumentaRisco = shap > 0;
  return (
    <div className="py-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-300">{rotulo}</span>
        <span className="text-slate-500">valor: {valor.toLocaleString("pt-BR")}</span>
      </div>
      <div className="mt-1 flex items-center gap-2">
        <div className="h-2.5 flex-1 rounded bg-slate-800">
          <div
            className={`h-2.5 rounded ${aumentaRisco ? "bg-red-500" : "bg-emerald-500"}`}
            style={{ width: `${largura}%` }}
          />
        </div>
        <span
          className={`w-24 text-right text-xs font-medium ${
            aumentaRisco ? "text-red-400" : "text-emerald-400"
          }`}
        >
          {aumentaRisco ? "↑ risco" : "↓ risco"} {Math.abs(shap).toFixed(2)}
        </span>
      </div>
    </div>
  );
}

export default function PainelCliente({
  cliente,
  acoes,
  carregando,
}: PainelClienteProps) {
  if (carregando) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <p className="animate-pulse text-sm text-slate-400">
          Carregando cliente...
        </p>
      </div>
    );
  }
  if (!cliente) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <p className="text-sm text-slate-400">
          Selecione um cliente na fila ao lado para ver os fatores de risco e a
          ação recomendada.
        </p>
      </div>
    );
  }

  const custo = acoes.find((a) => a.nome === cliente.acao_nome)?.custo;
  const maxAbs = Math.max(...cliente.fatores.map((f) => Math.abs(f.shap)), 0.01);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Cliente
          </p>
          <h3 className="text-xl font-semibold text-slate-100">
            {cliente.CustomerID}
          </h3>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Risco de churn
          </p>
          <p className="text-xl font-semibold text-red-400">
            {(cliente.prob * 100).toFixed(1)}%
          </p>
          <p className="text-xs text-slate-500">#{cliente.rank} no ranking</p>
        </div>
      </div>

      <div className="mt-4 rounded-lg bg-slate-800/60 p-3">
        <p className="text-xs uppercase tracking-wide text-slate-500">Perfil</p>
        <p className="mt-0.5 font-medium text-sky-300">{cliente.segmento}</p>
      </div>

      <div className="mt-3 rounded-lg border border-emerald-900 bg-emerald-950/50 p-3">
        <p className="text-xs uppercase tracking-wide text-emerald-500">
          Ação recomendada pelo agente
        </p>
        <p className="mt-0.5 font-medium text-emerald-300">
          {cliente.acao_nome}
        </p>
        <p className="mt-1 text-xs text-slate-400">
          aceitação esperada {(cliente.taxa_esperada * 100).toFixed(0)}%
          {custo !== undefined && <> · custo R$ {custo}</>}
        </p>
      </div>

      <h4 className="mt-5 text-sm font-medium text-slate-200">
        Por que o modelo aponta risco (SHAP)
      </h4>
      <div className="mt-2 divide-y divide-slate-800/60">
        {cliente.fatores.map((fator) => (
          <BarraFator
            key={fator.variavel}
            rotulo={fator.rotulo}
            shap={fator.shap}
            valor={fator.valor}
            maxAbs={maxAbs}
          />
        ))}
      </div>
    </div>
  );
}
