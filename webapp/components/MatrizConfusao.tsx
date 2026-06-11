import type { Metricas } from "@/lib/types";

interface MatrizConfusaoProps {
  metricas: Metricas;
}

function Celula({
  rotulo,
  valor,
  classe,
}: {
  rotulo: string;
  valor: number;
  classe: string;
}) {
  return (
    <div className={`rounded-lg p-4 text-center ${classe}`}>
      <p className="text-2xl font-semibold">{valor.toLocaleString("pt-BR")}</p>
      <p className="mt-1 text-xs opacity-80">{rotulo}</p>
    </div>
  );
}

export default function MatrizConfusao({ metricas }: MatrizConfusaoProps) {
  const { tp, fp, tn, fn } = metricas;
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <h3 className="mb-3 font-medium text-slate-200">Matriz de confusão</h3>
      <div className="grid grid-cols-2 gap-2">
        <Celula
          rotulo="Ficou e previsto ficar (TN)"
          valor={tn}
          classe="bg-slate-800 text-slate-300"
        />
        <Celula
          rotulo="Promoção desnecessária (FP)"
          valor={fp}
          classe="bg-amber-950 text-amber-300"
        />
        <Celula
          rotulo="Cancelamento perdido (FN)"
          valor={fn}
          classe="bg-red-950 text-red-300"
        />
        <Celula
          rotulo="Cancelamento detectado (TP)"
          valor={tp}
          classe="bg-emerald-950 text-emerald-300"
        />
      </div>
      <p className="mt-3 text-xs text-slate-500">
        Linhas: realidade · Colunas: previsão do modelo
      </p>
    </div>
  );
}
