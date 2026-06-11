"use client";

import type { Acao, ClienteDetalhe, ResultadoOferta } from "@/lib/types";
import { useEffect, useState } from "react";

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

function SimuladorOferta({ cliente }: { cliente: ClienteDetalhe }) {
  const [tentativas, setTentativas] = useState<ResultadoOferta[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    setTentativas([]);
    setErro(null);
  }, [cliente.CustomerID]);

  const ultima = tentativas[tentativas.length - 1] ?? null;
  const retido = tentativas.some((t) => t.aceitou);
  const custoTotal = tentativas.reduce(
    (soma, t) => soma + (t.aceitou ? t.custo : 0),
    0,
  );
  const jaTentadas = tentativas.map((t) => t.acao);
  const proximaAcao = ultima
    ? (ultima.alternativas.find((a) => !jaTentadas.includes(a)) ?? null)
    : cliente.acao;

  async function enviar(acao: string | null) {
    if (!acao) {
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      const res = await fetch("/api/py/simular_oferta", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_id: cliente.CustomerID, acao }),
      });
      if (!res.ok) {
        throw new Error(`Backend respondeu ${res.status}`);
      }
      const resultado = (await res.json()) as ResultadoOferta;
      setTentativas((anteriores) => [...anteriores, resultado]);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha na simulação");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mt-4 rounded-lg border border-slate-700 bg-slate-800/40 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">
        Simular envio da oferta
      </p>

      {tentativas.map((tentativa, indice) => (
        <div
          key={`${tentativa.acao}-${indice}`}
          className={`mt-2 rounded-lg p-2.5 text-sm ${
            tentativa.aceitou
              ? "bg-emerald-950/70 text-emerald-300"
              : "bg-amber-950/60 text-amber-300"
          }`}
        >
          {tentativa.aceitou ? "✅" : "❌"} {tentativa.acao_nome}:{" "}
          {tentativa.aceitou ? "oferta aceita" : "oferta recusada"}
          {tentativa.aceitou && (
            <p className="mt-1 text-xs text-slate-300">
              Cliente retido · risco{" "}
              {(tentativa.risco_antes * 100).toFixed(1)}% →{" "}
              <span className="font-semibold text-emerald-300">
                {(tentativa.risco_depois * 100).toFixed(1)}%
              </span>{" "}
              · custo R$ {tentativa.custo}
            </p>
          )}
        </div>
      ))}

      {erro && (
        <p className="mt-2 rounded bg-red-950 px-2 py-1.5 text-xs text-red-300">
          {erro}
        </p>
      )}

      {retido ? (
        <p className="mt-2 text-xs text-slate-400">
          🎉 Retenção concluída — custo total R$ {custoTotal}. (Efeito
          simulado: aceite reduz o risco em{" "}
          {((ultima?.reducao_risco_aceite ?? 0.6) * 100).toFixed(0)}%.)
        </p>
      ) : proximaAcao ? (
        <button
          onClick={() => enviar(proximaAcao)}
          disabled={enviando}
          className="mt-2 w-full rounded-lg bg-emerald-700 px-3 py-2 text-sm font-medium text-white transition hover:bg-emerald-600 disabled:opacity-50"
        >
          {enviando
            ? "Enviando oferta..."
            : tentativas.length === 0
              ? "📨 Simular envio da oferta recomendada"
              : "↻ Tentar próxima oferta do perfil"}
        </button>
      ) : (
        <p className="mt-2 text-xs text-slate-400">
          Todas as ofertas do perfil foram recusadas — encaminhar para
          tratamento manual.
        </p>
      )}
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

      <SimuladorOferta cliente={cliente} />

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
