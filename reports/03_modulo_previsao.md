# Modulo de Previsao (Dia N) - Resultados

- Split estratificado: **40,837 treino / 10,210 teste (20%)**, seed 42.
- Validacao cruzada 5-fold estratificada, apenas no treino.
- Desbalanceamento tratado com `class_weight='balanced'` (baseline) e `scale_pos_weight` (XGBoost) - sem SMOTE: os pesos deram recall equivalente sem custo extra.

## Validacao cruzada (5-fold, treino)

| modelo                         | recall          | f1              | roc_auc         | precision       |
|:-------------------------------|:----------------|:----------------|:----------------|:----------------|
| Regressao Logistica (baseline) | 0.565 +/- 0.013 | 0.442 +/- 0.009 | 0.617 +/- 0.009 | 0.363 +/- 0.008 |
| XGBoost                        | 0.565 +/- 0.010 | 0.482 +/- 0.008 | 0.678 +/- 0.008 | 0.420 +/- 0.009 |

## Ajuste do ponto de decisao (out-of-fold, sem tocar no teste)

Criterio: maximizar **F2** (recall pesa 2x a precisao), porque perder um cliente custa mais que oferecer promocao a quem nao cancelaria.

|   threshold |   recall |   precision |    f1 |    f2 |
|------------:|---------:|------------:|------:|------:|
|        0.2  |    0.967 |       0.308 | 0.467 | 0.677 |
|        0.25 |    0.938 |       0.322 | 0.479 | 0.679 |
|        0.3  |    0.894 |       0.335 | 0.488 | 0.67  |
|        0.35 |    0.841 |       0.351 | 0.495 | 0.658 |
|        0.4  |    0.768 |       0.368 | 0.497 | 0.631 |
|        0.45 |    0.674 |       0.391 | 0.494 | 0.588 |
|        0.5  |    0.565 |       0.42  | 0.482 | 0.528 |
|        0.55 |    0.447 |       0.455 | 0.451 | 0.449 |
|        0.6  |    0.327 |       0.491 | 0.393 | 0.351 |
|        0.65 |    0.224 |       0.538 | 0.316 | 0.253 |
|        0.7  |    0.143 |       0.584 | 0.229 | 0.168 |

**Threshold escolhido: 0.25**

## Avaliacao final no conjunto de teste

| modelo                         |   threshold |   recall |   precision |    f1 |   auc_roc |
|:-------------------------------|------------:|---------:|------------:|------:|----------:|
| Regressao Logistica (baseline) |        0.5  |    0.577 |       0.364 | 0.447 |     0.615 |
| XGBoost                        |        0.5  |    0.575 |       0.409 | 0.478 |     0.677 |
| XGBoost                        |        0.25 |    0.944 |       0.318 | 0.475 |     0.677 |

Matriz de confusao do XGBoost no threshold 0.25: TN=1,304 | FP=5,964 | FN=166 | TP=2,776

Leitura de negocio: dos clientes que cancelariam, o modelo detecta **94%** (recall). O custo disso sao 5,964 promocoes oferecidas a clientes que ficariam - barato comparado a perder 2,776 clientes detectaveis.

## Artefatos

- `models/xgb_model.json`, `models/logreg.joblib`, `models/threshold.json`
- `reports/figs/`: curva ROC, matriz de confusao, importancia de variaveis
- `data/processed/scores_teste.csv`: ranking de risco do teste (insumo do dashboard do Dia H)