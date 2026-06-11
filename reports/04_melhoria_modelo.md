# Melhoria do Modelo - menos falsos positivos, recall preservado

- Features derivadas usadas: **True** (AUC-PR CV3 0.4533 -> 0.4546)
- Tuning (30 candidatos, AUC-PR): CV5 0.4618 -> 0.4639
- Novo criterio de threshold: **max precisao com recall >= 90%** (out-of-fold) -> threshold 0.31

## Comparacao no mesmo conjunto de teste

| modelo                             |   threshold |   recall |   precision |   auc_roc |   auc_pr |   fp |   fn |   abordados |
|:-----------------------------------|------------:|---------:|------------:|----------:|---------:|-----:|-----:|------------:|
| Dia N (thr 0,25 - max F2)          |        0.25 |   0.9436 |      0.3176 |    0.6768 |   0.457  | 5965 |  166 |        8741 |
| Melhorado (thr 0.31 - recall>=90%) |        0.31 |   0.9082 |      0.3306 |    0.68   |   0.4571 | 5410 |  270 |        8082 |

**Falsos positivos: 5,965 -> 5,410 (+555 promocoes desnecessarias)**

Params do vencedor: {"colsample_bytree": 0.621079969138713, "gamma": 4.015698781899479, "learning_rate": 0.029532528683590346, "max_depth": 5, "min_child_weight": 6, "n_estimators": 810, "reg_alpha": 0.1805795401088166, "reg_lambda": 4.25886123015157, "subsample": 0.7283120259886944}