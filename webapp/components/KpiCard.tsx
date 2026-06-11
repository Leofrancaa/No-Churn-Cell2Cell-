interface KpiCardProps {
  rotulo: string;
  valor: string;
  detalhe?: string;
  destaque?: "bom" | "ruim" | "neutro";
}

const CORES = {
  bom: "text-emerald-400",
  ruim: "text-red-400",
  neutro: "text-sky-400",
} as const;

export default function KpiCard({
  rotulo,
  valor,
  detalhe,
  destaque = "neutro",
}: KpiCardProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-400">{rotulo}</p>
      <p className={`mt-1 text-2xl font-semibold ${CORES[destaque]}`}>{valor}</p>
      {detalhe && <p className="mt-1 text-xs text-slate-500">{detalhe}</p>}
    </div>
  );
}
