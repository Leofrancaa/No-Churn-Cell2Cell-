"use client";

import KpiCard from "@/components/KpiCard";
import type { ResultadoCampanha } from "@/lib/types";
import { useState } from "react";

const MOEDA = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

export default function Campanha() {
  const [topN, setTopN] = useState(200);
  const [ltv, setLtv] = useState(500);
  const [resultado, setResultado] = useState<ResultadoCampanha | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function simular() {
    setCarregando(true);
    setErro(null);
    try {
      const res = await fetch(
        `/api/py/simular_campanha?top_n=${topN}&ltv=${ltv}`,
      );
      if (!res.ok) {
        throw new Error(`Backend respondeu ${res.status}`);
      }
      setResultado((await res.json()) as ResultadoCampanha);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha na simulação");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-5">
      <h2 className="text-lg font-medium text-slate-100">
        Simulação de campanha — e se acionarmos o topo do ranking?
      </h2>
      <p className="mt-1 text-sm text-slate-400">
        Valor esperado de enviar a oferta recomendada pela política aprendida
        aos N clientes de maior risco, comparado a não fazer nada.
      </p>

      <div className="mt-4 flex flex-wrap items-end gap-4">
        <label className="text-sm text-slate-300">
          Clientes acionados (top N)
          <input
            type="range"
            min={50}
            max={1000}
            step={50}
            value={topN}
            onChange={(e) => setTopN(Number(e.target.value))}
            className="mt-1 block w-56 accent-sky-500"
          />
          <span className="text-xs text-slate-400">
            top {topN.toLocaleString("pt-BR")}
          </span>
        </label>
        <label className="text-sm text-slate-300">
          Valor do cliente (LTV, R$)
          <input
            type="number"
            min={50}
            max={100000}
            step={50}
            value={ltv}
            onChange={(e) => setLtv(Number(e.target.value))}
            className="mt-1 block w-32 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-slate-100 outline-none focus:border-sky-500"
          />
        </label>
        <button
          onClick={simular}
          disabled={carregando}
          className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-500 disabled:opacity-50"
        >
          {carregando ? "Simulando..." : "▶ Simular campanha"}
        </button>
      </div>

      {erro && (
        <p className="mt-3 rounded-lg bg-red-950 px-3 py-2 text-sm text-red-300">
          {erro}
        </p>
      )}

      {resultado && (
        <>
          <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-5">
            <KpiCard
              rotulo="Cancelariam sem ação"
              valor={resultado.perdidos_sem_acao.toLocaleString("pt-BR")}
              destaque="ruim"
              detalhe={`entre os top ${resultado.top_n}`}
            />
            <KpiCard
              rotulo="Clientes salvos"
              valor={`≈ ${resultado.salvos_esperados.toLocaleString("pt-BR")}`}
              destaque="bom"
              detalhe="cancelaria e aceitou"
            />
            <KpiCard
              rotulo="Custo das ofertas"
              valor={MOEDA.format(resultado.custo_esperado)}
              detalhe="pago só quando aceita"
            />
            <KpiCard
              rotulo="Receita preservada"
              valor={MOEDA.format(resultado.receita_preservada)}
              destaque="bom"
              detalhe={`salvos × LTV ${MOEDA.format(resultado.ltv)}`}
            />
            <KpiCard
              rotulo="ROI da campanha"
              valor={`${resultado.roi.toLocaleString("pt-BR")}×`}
              destaque={resultado.roi > 0 ? "bom" : "ruim"}
              detalhe="(preservada − custo) / custo"
            />
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-left text-xs text-slate-400">
                  <th className="py-2 pr-4">Perfil</th>
                  <th className="py-2 pr-4">Oferta aplicada</th>
                  <th className="py-2 pr-4">Clientes</th>
                  <th className="py-2 pr-4">Aceites esperados</th>
                  <th className="py-2 pr-4">Salvos esperados</th>
                  <th className="py-2">Custo</th>
                </tr>
              </thead>
              <tbody>
                {resultado.por_segmento.map((linha) => (
                  <tr
                    key={linha.segmento}
                    className="border-b border-slate-800/50"
                  >
                    <td className="py-2 pr-4 text-sky-300">{linha.segmento}</td>
                    <td className="py-2 pr-4 text-emerald-300">
                      {linha.acao_nome}
                    </td>
                    <td className="py-2 pr-4">
                      {linha.clientes.toLocaleString("pt-BR")}
                    </td>
                    <td className="py-2 pr-4">
                      {linha.aceites_esperados.toLocaleString("pt-BR")}
                    </td>
                    <td className="py-2 pr-4">
                      {linha.salvos_esperados.toLocaleString("pt-BR")}
                    </td>
                    <td className="py-2">{MOEDA.format(linha.custo)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Premissas: cliente &quot;salvo&quot; = cancelaria (probabilidade do
            modelo) e aceitou a oferta (taxa do simulador); custo incorre
            apenas no aceite. Valores esperados, não sorteios.
          </p>
        </>
      )}
    </section>
  );
}
