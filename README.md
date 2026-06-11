# Sistema Inteligente de Retencao de Clientes (Churn - Cell2Cell)

Pipeline completo: **prever** (XGBoost) -> **explicar** (SHAP) -> **agir**
(agente de recomendacao com feedback simulado), integrado em dashboard web
com login. Dataset: Cell2Cell (~51 mil clientes).

## Estrutura

```
data/raw/        cell2celltrain.csv (original, nunca editar)
data/processed/  dataset tratado, scores, shap_teste.json, retencao.json
src/             explore | preprocess | features | train | tune | explain |
                 retention | export_dashboard_data
models/          xgb_model.json, logreg.joblib, threshold.json
reports/         01 perfil bruto | 02 tratamento | 03 previsao |
                 04 melhoria | 05 retencao
notebooks/       churn_cell2cell.ipynb (auto-contido, pronto para o Colab)
dashboard/       app.py (Streamlit - uso local/prototipagem)
webapp/          Next.js + FastAPI com login (deploy na Vercel - ver webapp/README.md)
```

## Como rodar (pipeline completo)

```powershell
D:\Churn\.venv\Scripts\python.exe src\explore.py     # perfil do dataset bruto
D:\Churn\.venv\Scripts\python.exe src\preprocess.py  # tratamento + diagnostico
D:\Churn\.venv\Scripts\python.exe src\train.py       # baseline + XGBoost (Dia N)
D:\Churn\.venv\Scripts\python.exe src\tune.py        # features + tuning + threshold
D:\Churn\.venv\Scripts\python.exe src\explain.py     # SHAP individual (Dia H)
D:\Churn\.venv\Scripts\python.exe src\retention.py   # simulador + agente (Dia H)
D:\Churn\.venv\Scripts\python.exe src\export_dashboard_data.py  # dados p/ webapp
```

## Status

- [x] Dia M - Dataset tratado + analise exploratoria
- [x] Dia N - Modulo de previsao (Regressao Logistica + XGBoost)
- [x] Dia H - Modulo de retencao + dashboard (SHAP + agente Thompson
      Sampling + pagina do Analista no webapp)

## Decisoes importantes

- `preprocess_params.json` guarda medianas e frequencias aprendidas no
  treino, para aplicar o mesmo tratamento em dados novos (sem vazamento).
- O modelo final usa as features derivadas de `src/features.py` - dados
  novos precisam passar por `adicionar_features()` apos o preprocess.
- Threshold 0,31 = maxima precisao com recall >= 90% (out-of-fold).
- Aceitacao das ofertas e simulada (validacao com campanha real e
  trabalho futuro, conforme o escopo).
