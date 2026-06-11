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
