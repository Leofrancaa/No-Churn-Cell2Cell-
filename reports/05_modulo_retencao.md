# Modulo de Retencao + Dashboard (Dia H)

Fecha o ciclo **prever -> explicar -> agir** do sistema.

## 1. Explicar: SHAP individual (src/explain.py)

- TreeExplainer sobre o XGBoost melhorado, nos 10.210 clientes de teste.
- Para cada cliente: os 5 fatores que mais empurram o risco para cima ou
  para baixo, com rotulo legivel para a equipe de retencao.
- Fatores globais mais influentes: dias com o aparelho atual, receita por
  minuto (preco pago), meses de contrato, variacao de minutos, mensalidade.

## 2. Agir: simulador + agente (src/retention.py)

**Segmentacao interpretavel** (regras sobre features derivadas, cortes no
quantil 75): Insatisfeito com o servico (4.588 clientes no teste),
Sensivel a preco (2.562), Aparelho desatualizado (1.386), Perfil geral
(1.204), Fim de fidelizacao (470).

**Simulador**: matriz oculta P(aceitar | segmento, acao) com 4 acoes de
custos diferentes (desconto R$30, upgrade R$80, suporte R$8, bonus R$15).
A acao que ataca a dor do segmento converte mais - o agente nao sabe disso.

**Agente**: Thompson Sampling (Beta-Bernoulli por segmento x acao),
8.000 ofertas simuladas. Resultado:

- Encontrou a acao otima nos **5 de 5 segmentos** sem nunca ver a matriz.
- Taxa de aceitacao convergiu para **47,2%** (acaso ~30%).
- Curva de aprendizado: aceitacao sobe, arrependimento medio cai.

## 3. Dashboard (webapp, pagina "Analista de Retencao")

- **Fila de retencao**: top 200 riscos com busca por ID; clicar abre o
  painel do cliente.
- **Painel do cliente**: risco, perfil, acao recomendada (com taxa esperada
  e custo) e os fatores SHAP individuais (barras vermelho/verde).
- **Modo simulacao**: curva de aprendizado do agente + politica aprendida
  por perfil (taxas estimadas vs custo de cada acao).
- Endpoints: `/api/py/analista` e `/api/py/cliente/{id}` (autenticados).

## 4. Ativacao simulada e resultado (interativo no dashboard)

- **Oferta individual** (`POST /api/py/simular_oferta`): botao "Simular
  envio da oferta" no painel do cliente. O aceite e sorteado com a taxa
  REAL (oculta) do par segmento x acao. Aceitou -> cliente retido, risco
  cai 60% (premissa documentada) e o custo e contabilizado; recusou ->
  o analista pode tentar a proxima oferta na ordem aprendida pelo agente,
  ate esgotar (encaminhamento manual).
- **Campanha** (`GET /api/py/simular_campanha`): valor esperado de acionar
  os top N riscos com a politica aprendida. Premissas: salvo = cancelaria
  (prob do modelo) E aceita (taxa do simulador); custo so no aceite.
  Exemplo (top 500, LTV R$600): ~395 cancelariam sem acao, ~211 salvos,
  custo ~R$6,6 mil, receita preservada ~R$127 mil, ROI ~18x.

## Exemplo real do ciclo completo

Cliente 3333054: risco 94,6% -> fator n.1 "Receita por minuto (preco pago)"
-> segmento "Sensivel a preco" -> acao recomendada "Desconto na mensalidade".

## Limites (escopo)

A aceitacao das ofertas e simulada; validar com dados reais de campanha
permanece como trabalho futuro, como definido no escopo.
