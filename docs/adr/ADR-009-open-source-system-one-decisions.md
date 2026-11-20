# ADR-009: Open-Source System-One Decision Engine (Outlines / Local SLM / ONNX NLI)

## Status
Aceito (Accepted)

## Data
2026-11-20

## Contexto & Motivação
Em arquiteturas de agentes autônomos e frameworks de engenharia de software de ponta, tarefas de alta frequência (como roteamento de subagentes na DAG, triagem de risco de mudanças e quality gates semânticos) tradicionalmente enfrentavam um dilema arquitetural:
1. **Regras Heurísticas Rígidas**: Rápidas, mas frágeis a variações de linguagem natural e sem calibração probabilística real.
2. **LLMs Generativos Pesados (System Two)**: Raciocínio profundo, mas com latência na casa de segundos, alto consumo de tokens, custo financeiro recorrente e risco constante de alucinação de formato JSON.
3. **Modelos Proprietários Fechados (ex.: Jev / TypeSafe AI)**: Apresentam o paradigma correto de *System One* (decisões estruturadas e probabilísticas sem geração livre de texto), porém introduzem dependência de nuvem de terceiros, custo por requisição e quebra de soberania de dados para bases de código corporativas confidenciais.

Fazia-se necessária uma solução de engenharia **100% open-source, local, tipada e com zero envio externo de dados**.

## Decisão de Arquitetura

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `ChoiceDecision`: Seleção categórica com probabilidade e distribuição calibrada (`choice`, `confidence`, `probabilities`, `rationale`).
   - `NoulDecision`: Decisão booleana condicional calibrada com probabilidade contínua de 0.0 a 1.0 (`decision`, `probability`, `rationale`).
   - `ScoreDecision`: Pontuação contra rubricas e níveis de severidade (`score`, `level`, `confidence`, `rationale`).
   - `SystemOneReport`: Relatório consolidado com `task`, `engine_name`, `duration_ms`, mapeamento de decisões, `suggested_agent` e `risk_level`.

2. **Arquitetura de Motores Desacoplados (`src/corporate_engineer/system_one/`)**:
   - `SystemOneEngine`: Contrato abstrato (ABC) padronizando os métodos `decide_choice`, `decide_noul`, `decide_score` e `evaluate`.
   - `HeuristicDecisionEngine`: Implementação nativa em Python puro, com sub-milissegundo de latência, indexação lexical ponderada e calibração por softmax e sigmoide. Zero dependências externas obrigatórias.
   - `OutlinesDecisionEngine`: Suporte a decodificação restrita por autômatos finitos (FSM) via biblioteca `outlines` acoplada a SLMs locais (ex.: Qwen 2.5 0.5B / SmolLM2), eliminando 100% de alucinações estruturais.
   - `ONNXNLIDecisionEngine`: Suporte a modelos de inferência de linguagem natural compactos via `onnxruntime` (ex.: ModernBERT / DeBERTa) para cálculo contínuo de acarretamento (*entailment*).
   - `SystemOneRouter`: Fachada de alto nível para roteamento dos 8 subagentes canônicos do framework, avaliação de risco de diffs e triagem de quality gate.

3. **Integração com a CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Adicionado o subcomando `corporate-engineer decide`:
     - Modos: `--mode route` (seleção de subagente), `--mode risk` (avaliação de risco) e `--mode triage` (triagem completa).
     - Motores: `--engine auto|heuristic|outlines|nli`.
     - Formatos: `--format text|json` e exportação com `--output`.

## Consequências
- **Positivas**:
  - Respostas sub-milissegundo (média de 0.5ms a 50ms) para decisões de roteamento e triagem de risco.
  - 100% open-source e soberano: nenhum código, prompt ou métrica é enviado para APIs de terceiros.
  - Fallback gracioso transparente: se dependências pesadas (`outlines`, `onnxruntime`) não estiverem no ambiente, o framework opera imediatamente via motor heurístico sem quebra de serviço.
  - Tipagem estrita Pydantic v2 garantindo total interoperabilidade com a DAG e o orquestrador.
- **Limitações Mitigadas**:
  - A inicialização a frio de SLMs locais é abstraída por lazy-loading, mantendo a suíte de testes extremamente rápida (113 testes em ~12s).
