"use client";

import KpiCard from "@/components/KpiCard";
import MatrizConfusao from "@/components/MatrizConfusao";
import NavBar from "@/components/NavBar";
import {
  GraficoDistribuicao,
  GraficoImportancias,
  GraficoRoc,
} from "@/components/Graficos";
import type { DashboardData, Metricas } from "@/lib/types";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

export default function Dashboard() {
  const router = useRouter();
  const [dados, setDados] = useState<DashboardData | null>(null);
  const [metricas, setMetricas] = useState<Metricas | null>(null);
  const [threshold, setThreshold] = useState<number>(0.25);
  const [erro, setErro] = useState<string | null>(null);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    async function carregar() {
      try {
        const res = await fetch("/api/py/dashboard");
        if (res.status === 401) {
          router.push("/login");
          return;
        }
        if (!res.ok) {
          throw new Error(`Backend respondeu ${res.status}`);
        }
        const corpo = (await res.json()) as DashboardData;
        setDados(corpo);
        setMetricas(corpo.metricas);
        setThreshold(corpo.meta.threshold_oficial);
      } catch (err) {
        setErro(
          err instanceof Error ? err.message : "Falha ao carregar o painel",
        );
      }
    }
    carregar();
  }, [router]);

  function aoMoverSlider(novo: number) {
    setThreshold(novo);
    if (debounce.current) {
      clearTimeout(debounce.current);
    }
    debounce.current = setTimeout(async () => {
      try {
        const res = await fetch(`/api/py/metrics?threshold=${novo}`);
        if (res.ok) {
          setMetricas((await res.json()) as Metricas);
        }
      } catch {
        // mantem as metricas anteriores; o slider continua utilizavel
      }
    }, 250);
  }

  if (erro) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950">
        <p className="rounded-lg bg-red-950 px-4 py-3 text-red-300">{erro}</p>
      </main>
    );
  }

  if (!dados || !metricas) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950">
        <p className="animate-pulse text-slate-400">Carregando painel...</p>
      </main>
    );
  }

  const { meta } = dados;

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-6 text-slate-100">
      <div className="mx-auto max-w-6xl">
        <NavBar />
        <header className="mt-5">
          <h1 className="text-2xl font-semibold">
            🔧 Diagnóstico do modelo de previsão
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            XGBoost avaliado em {meta.n_teste.toLocaleString("pt-BR")} clientes
            de teste (nunca vistos no treino)
          </p>
        </header>

        <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-medium">Ponto de decisão</h2>
            <span className="text-sm text-slate-400">
              oficial: {meta.threshold_oficial.toFixed(2)} (máx. F2 out-of-fold)
            </span>
          </div>
          <input
            type="range"
            min={0.05}
            max={0.95}
            step={0.05}
            value={threshold}
            onChange={(e) => aoMoverSlider(Number(e.target.value))}
            className="mt-3 w-full accent-sky-500"
          />
          <p className="text-sm text-slate-400">
            threshold ={" "}
            <span className="font-semibold text-sky-400">
              {threshold.toFixed(2)}
            </span>{" "}
            — a equipe abordaria{" "}
            <span className="font-semibold text-slate-200">
              {metricas.abordados.toLocaleString("pt-BR")}
            </span>{" "}
            clientes e capturaria{" "}
            <span className="font-semibold text-emerald-400">
              {(metricas.recall * 100).toFixed(0)}%
            </span>{" "}
            dos cancelamentos
          </p>
        </section>

        <section className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-5">
          <KpiCard
            rotulo="AUC-ROC"
            valor={meta.auc.toFixed(3)}
            detalhe="independe do threshold"
          />
          <KpiCard
            rotulo="Recall (detecção)"
            valor={`${(metricas.recall * 100).toFixed(1)}%`}
            destaque="bom"
          />
          <KpiCard
            rotulo="Precisão"
            valor={`${(metricas.precision * 100).toFixed(1)}%`}
          />
          <KpiCard
            rotulo="Cancelamentos perdidos"
            valor={metricas.fn.toLocaleString("pt-BR")}
            destaque="ruim"
            detalhe="falsos negativos"
          />
          <KpiCard
            rotulo="Promoções extras"
            valor={metricas.fp.toLocaleString("pt-BR")}
            detalhe="falsos positivos"
          />
        </section>

        <section className="mt-4 grid gap-4 lg:grid-cols-2">
          <MatrizConfusao metricas={metricas} />
          <GraficoRoc roc={dados.roc} auc={meta.auc} />
        </section>

        <section className="mt-4">
          <GraficoDistribuicao
            distribuicao={dados.distribuicao}
            threshold={threshold}
          />
        </section>

        <section className="mt-4">
          <GraficoImportancias importancias={dados.importancias} />
        </section>

        <section className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-5">
          <h3 className="mb-3 font-medium text-slate-200">
            Topo do ranking de risco
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-left text-slate-400">
                  <th className="py-2 pr-4">#</th>
                  <th className="py-2 pr-4">Cliente</th>
                  <th className="py-2 pr-4">Prob. de churn</th>
                  <th className="py-2">Cancelou de fato?</th>
                </tr>
              </thead>
              <tbody>
                {dados.ranking.map((cliente) => (
                  <tr
                    key={cliente.CustomerID}
                    className="border-b border-slate-800/50"
                  >
                    <td className="py-2 pr-4 text-slate-500">
                      {cliente.rank_risco}
                    </td>
                    <td className="py-2 pr-4">{cliente.CustomerID}</td>
                    <td className="py-2 pr-4 font-medium text-sky-400">
                      {(cliente.prob_churn * 100).toFixed(1)}%
                    </td>
                    <td className="py-2">
                      {cliente.churn_real === 1 ? (
                        <span className="text-red-400">Sim</span>
                      ) : (
                        <span className="text-slate-400">Não</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <footer className="mt-6 text-center text-xs text-slate-600">
          Falso positivo custa uma promoção; falso negativo custa o cliente.
        </footer>
      </div>
    </main>
  );
}
