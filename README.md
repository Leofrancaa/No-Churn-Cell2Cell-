# Sistema Inteligente de Retencao de Clientes (Churn - Cell2Cell)

Pipeline completo: **prever** (XGBoost) -> **explicar** (SHAP) -> **agir**
(agente de recomendacao com feedback simulado), integrado em dashboard
Streamlit. Dataset: Cell2Cell (~51 mil clientes).

## Estrutura

```
data/raw/        cell2celltrain.csv (original, nunca editar)
data/processed/  cell2cell_tratado.csv + preprocess_params.json
src/             explore.py | preprocess.py | train.py (modelos + threshold)
models/          xgb_model.json, logreg.joblib, threshold.json
reports/         01_perfil_bruto | 02_diagnostico_tratamento | 03_modulo_previsao
notebooks/       churn_cell2cell.ipynb (auto-contido, pronto para o Colab)
dashboard/       app.py (Streamlit - uso local/prototipagem)
webapp/          Next.js + FastAPI com login (deploy na Vercel - ver webapp/README.md)
notebooks/       experimentos
```

## Como rodar

```powershell
D:\Churn\.venv\Scripts\python.exe src\explore.py     # perfil do dataset bruto
D:\Churn\.venv\Scripts\python.exe src\preprocess.py  # gera dataset tratado + diagnostico
D:\Churn\.venv\Scripts\python.exe src\train.py       # treina modelos + relatorio Dia N
D:\Churn\.venv\Scripts\python.exe -m streamlit run dashboard\app.py  # dashboard
```

## Status

- [x] Dia M - Dataset tratado + analise exploratoria
- [x] Dia N - Modulo de previsao (Regressao Logistica + XGBoost)
- [ ] Dia H - Modulo de retencao + dashboard

## Decisoes importantes

- `preprocess_params.json` guarda medianas e frequencias aprendidas no
  treino, para aplicar o mesmo tratamento em dados novos (sem vazamento).
- Desbalanceamento (28,8% churn) sera tratado no treinamento (dentro da
  validacao cruzada), nao no pre-processamento.
- Outliers mantidos: XGBoost e robusto e uso extremo e sinal real.
