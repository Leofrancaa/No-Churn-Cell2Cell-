export interface Meta {
  auc: number;
  threshold_oficial: number;
  n_teste: number;
  taxa_churn: number;
}

export interface Metricas {
  threshold: number;
  tp: number;
  fp: number;
  tn: number;
  fn: number;
  recall: number;
  precision: number;
  f1: number;
  abordados: number;
}

export interface PontoRoc {
  fpr: number;
  tpr: number;
}

export interface FaixaDistribuicao {
  score: number;
  ficou: number;
  cancelou: number;
}

export interface Importancia {
  variavel: string;
  ganho: number;
}

export interface ClienteRanking {
  CustomerID: number;
  prob_churn: number;
  churn_real: number;
  rank_risco: number;
}

export interface DashboardData {
  meta: Meta;
  roc: PontoRoc[];
  distribuicao: FaixaDistribuicao[];
  importancias: Importancia[];
  ranking: ClienteRanking[];
  metricas: Metricas;
}

export interface FatorShap {
  variavel: string;
  rotulo: string;
  shap: number;
  valor: number;
}

export interface ClienteFila {
  CustomerID: number;
  prob: number;
  rank: number;
  segmento: string;
  acao_nome: string;
  taxa_esperada: number;
}

export interface ClienteDetalhe extends ClienteFila {
  acao: string;
  fatores: FatorShap[];
}

export interface Acao {
  id: string;
  nome: string;
  custo: number;
}

export interface LinhaPolitica {
  acao: string;
  tentativas: number;
  aceites: number;
  taxa_estimada: number;
  taxa_real_oculta: number;
}

export interface PontoCurva {
  rodada: number;
  taxa_aceite: number;
  regret_medio: number;
}

export interface Retencao {
  acoes: Acao[];
  segmentos: string[];
  distribuicao_segmentos: Record<string, number>;
  politica: Record<string, LinhaPolitica[]>;
  melhor_acao: Record<string, string>;
  curva: PontoCurva[];
  rodadas: number;
}

export interface ShapGlobal {
  variavel: string;
  rotulo: string;
  impacto_medio: number;
}

export interface AnalistaData {
  meta: Meta;
  fila: ClienteFila[];
  retencao: Retencao;
  shap_global: ShapGlobal[];
}

export interface ResultadoOferta {
  CustomerID: number;
  segmento: string;
  acao: string;
  acao_nome: string;
  custo: number;
  aceitou: boolean;
  risco_antes: number;
  risco_depois: number;
  reducao_risco_aceite: number;
  alternativas: string[];
}

export interface SegmentoCampanha {
  segmento: string;
  acao_nome: string;
  clientes: number;
  aceites_esperados: number;
  salvos_esperados: number;
  custo: number;
}

export interface ResultadoCampanha {
  top_n: number;
  ltv: number;
  aceites_esperados: number;
  salvos_esperados: number;
  perdidos_sem_acao: number;
  custo_esperado: number;
  receita_preservada: number;
  roi: number;
  por_segmento: SegmentoCampanha[];
}
