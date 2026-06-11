# Diagnostico do Tratamento de Dados - Cell2Cell

- Dataset bruto: **51,047 linhas x 58 colunas**
- Dataset tratado: **51,047 linhas x 73 colunas** (nenhuma linha removida)
- NaN restantes: **0**
- Colunas nao numericas restantes: **0**
- Alvo: Churn = 1 em **28.82%** dos clientes (desbalanceamento moderado - sera tratado no treinamento, nao aqui)

## Acoes aplicadas

| Coluna(s) | Acao | Linhas afetadas | Motivo |
|---|---|---:|---|
| Churn | Mapeado Yes/No -> 1/0 | 51,047 | Alvo binario exigido pelos modelos |
| ChildrenInHH, HandsetRefurbished, HandsetWebCapable, TruckOwner, RVOwner, BuysViaMailOrder, RespondsToMailOffers, OptOutMailings, NonUSTravel, OwnsComputer, HasCreditCard, NewCellphoneUser, NotNewCellphoneUser, OwnsMotorcycle, MadeCallToRetentionTeam | Mapeadas Yes/No -> 1/0 | 51,047 | 15 colunas binarias; evita one-hot desnecessario |
| Homeownership | Convertida em flag HomeownershipKnown (1/0) | 17,060 | 33% 'Unknown'; a coluna so informa se o dado existe, nao o valor |
| MaritalStatus | One-hot (Yes/No/Unknown como 3 colunas) | 19,700 | 39% 'Unknown' e informacao demais para descartar; 'Unknown' vira categoria propria |
| HandsetPrice | 'Unknown'->NaN, flag de conhecido, imputada mediana (60.0) | 28,982 | 57% 'Unknown'; flag preserva o padrao de ausencia, mediana evita distorcer a escala |
| AgeHH1 | 0->NaN, flag de conhecido, imputada mediana (42.0) | 14,826 | Idade 0 nao existe; zero codifica 'nao informado' |
| AgeHH2 | 0->NaN, flag de conhecido, imputada mediana (44.0) | 26,996 | Idade 0 nao existe; zero codifica 'nao informado' |
| CurrentEquipmentDays | Negativos->NaN, imputada mediana (330.0) | 77 | Dias de uso do aparelho nao podem ser negativos (erro de registro) |
| MonthlyRevenue, MonthlyMinutes, TotalRecurringCharge, DirectorAssistedCalls, OverageMinutes, RoamingCalls | Flag MissingBillingInfo + imputacao por mediana | 156 | As mesmas 156 linhas (0,31%) nao tem nenhum dado de fatura; a flag preserva essa informacao |
| PercChangeMinutes | Imputada mediana (-5.0) | 367 | NaN residual (<1%); mediana e robusta a outliers |
| PercChangeRevenues | Imputada mediana (-0.3) | 367 | NaN residual (<1%); mediana e robusta a outliers |
| Handsets | Imputada mediana (1.0) | 1 | NaN residual (<1%); mediana e robusta a outliers |
| HandsetModels | Imputada mediana (1.0) | 1 | NaN residual (<1%); mediana e robusta a outliers |
| CreditRating | Mapeado para escala ordinal 1-7 | 51,047 | Categorias tem ordem natural (1-Highest ... 7-Lowest) |
| PrizmCode | One-hot (4 colunas) | 51,047 | Baixa cardinalidade e sem ordem natural |
| Occupation | One-hot (8 colunas) | 51,047 | Baixa cardinalidade e sem ordem natural |
| ServiceArea | Frequency encoding (proporcao de clientes na area) | 24 | 747 categorias inviabilizam one-hot; frequencia captura porte da area sem usar o alvo (sem vazamento) |
| CustomerID | Movido para indice (fora das features) | 51,047 | Identificador nao tem valor preditivo; mantido para rastrear clientes |

## Decisoes que ficaram para a fase de treinamento (de proposito)

- **Desbalanceamento de classes**: SMOTE/class_weight serao aplicados dentro da validacao cruzada para nao vazar informacao entre folds.
- **Outliers**: nao foram cortados. XGBoost (arvores) e robusto a outliers; cortar agora destruiria sinal real de uso extremo.
- **Escalonamento**: apenas a Regressao Logistica precisa; o StandardScaler entrara no pipeline dela, ajustado so no treino.

## Validacao sugerida

1. Conferir que nenhuma linha foi perdida (contagem acima).
2. Conferir que nao restam NaN nem colunas de texto.
3. Conferir as medianas usadas em `preprocess_params.json`.
4. Conferir que a taxa de churn nao mudou apos o tratamento.