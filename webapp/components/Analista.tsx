"use client";

import Campanha from "@/components/Campanha";
import NavBar from "@/components/NavBar";
import PainelCliente from "@/components/PainelCliente";
import Simulacao from "@/components/Simulacao";
import type { AnalistaData, ClienteDetalhe } from "@/lib/types";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function Analista() {
  const router = useRouter();
  const [dados, setDados] = useState<AnalistaData | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [busca, setBusca] = useState("");
  const [cliente, setCliente] = useState<ClienteDetalhe | null>(null);
  const [carregandoCliente, setCarregandoCliente] = useState(false);

  useEffect(() => {
    async function carregar() {
      try {
        const res = await fetch("/api/py/analista");
        if (res.status === 401) {
          router.push("/login");
          return;
        }
        if (!res.ok) {
          throw new Error(`Backend respondeu ${res.status}`);
        }
        setDados((await res.json()) as AnalistaData);
      } catch (err) {
        setErro(err instanceof Error ? err.message : "Falha ao carregar");
      }
    }
    carregar();
  }, [router]);

  async function selecionar(customerId: number) {
    setCarregandoCliente(true);
    try {
      const res = await fetch(`/api/py/cliente/${customerId}`);
      if (res.ok) {
        setCliente((await res.json()) as ClienteDetalhe);
      }
    } catch {
      // mantem o painel anterior
    } finally {
      setCarregandoCliente(false);
    }
  }

  if (erro) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950">
        <p className="rounded-lg bg-red-950 px-4 py-3 text-red-300">{erro}</p>
      </main>
    );
  }
  if (!dados) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950">
        <p className="animate-pulse text-slate-400">Carregando painel...</p>
      </main>
    );
  }

  const filaFiltrada = busca
    ? dados.fila.filter((c) => String(c.CustomerID).includes(busca.trim()))
    : dados.fila;

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-6 text-slate-100">
      <div className="mx-auto max-w-6xl">
        <NavBar />

        <header className="mt-5">
          <h1 className="text-2xl font-semibold">
            📋 Fila de retenção — maiores riscos
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Top {dados.fila.length} clientes por probabilidade de churn, com o
            motivo do risco (SHAP) e a oferta que o agente aprendeu a recomendar
            para cada perfil.
          </p>
        </header>

        <div className="mt-5 grid gap-4 lg:grid-cols-[1.2fr_1fr]">
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <input
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar por ID do cliente..."
              className="mb-3 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500"
            />
            <div className="max-h-[560px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-slate-900">
                  <tr className="border-b border-slate-800 text-left text-xs text-slate-400">
                    <th className="py-2 pr-3">#</th>
                    <th className="py-2 pr-3">Cliente</th>
                    <th className="py-2 pr-3">Risco</th>
                    <th className="py-2 pr-3">Perfil</th>
                    <th className="py-2">Ação sugerida</th>
                  </tr>
                </thead>
                <tbody>
                  {filaFiltrada.map((linha) => (
                    <tr
                      key={linha.CustomerID}
                      onClick={() => selecionar(linha.CustomerID)}
                      className={`cursor-pointer border-b border-slate-800/50 transition hover:bg-slate-800/60 ${
                        cliente?.CustomerID === linha.CustomerID
                          ? "bg-slate-800"
                          : ""
                      }`}
                    >
                      <td className="py-2 pr-3 text-slate-500">{linha.rank}</td>
                      <td className="py-2 pr-3">{linha.CustomerID}</td>
                      <td className="py-2 pr-3 font-medium text-red-400">
                        {(linha.prob * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 pr-3 text-xs text-sky-300">
                        {linha.segmento}
                      </td>
                      <td className="py-2 text-xs text-emerald-300">
                        {linha.acao_nome}
                      </td>
                    </tr>
                  ))}
                  {filaFiltrada.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-slate-500">
                        Nenhum cliente encontrado entre os maiores riscos.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <PainelCliente
            cliente={cliente}
            acoes={dados.retencao.acoes}
            carregando={carregandoCliente}
          />
        </div>

        <Campanha />

        <Simulacao retencao={dados.retencao} />

        <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-5">
          <h3 className="font-medium text-slate-200">
            Fatores de risco mais influentes na base (visão global)
          </h3>
          <div className="mt-3 grid gap-1.5">
            {dados.shap_global.slice(0, 10).map((fator) => {
              const max = dados.shap_global[0].impacto_medio;
              return (
                <div key={fator.variavel} className="flex items-center gap-3">
                  <span className="w-64 truncate text-xs text-slate-300">
                    {fator.rotulo}
                  </span>
                  <div className="h-2 flex-1 rounded bg-slate-800">
                    <div
                      className="h-2 rounded bg-sky-500"
                      style={{
                        width: `${(fator.impacto_medio / max) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="w-12 text-right text-xs text-slate-500">
                    {fator.impacto_medio.toFixed(2)}
                  </span>
                </div>
              );
            })}
          </div>
        </section>

        <footer className="mt-6 text-center text-xs text-slate-600">
          Aceitação das ofertas simulada — validação com campanha real é
          trabalho futuro.
        </footer>
      </div>
    </main>
  );
}
