# ADR-015: Autonomous Benchmark & Evaluation Harness para Motores do Sistema 1

## Status
Aceito (Accepted)

## Data
2026-11-22

## Contexto & Motivação
Com a evolução do Sistema 1 no projeto `corporate-engineer` (IMP-0013, IMP-0014, ADR-013), múltiplos motores de decisão passaram a coexistir:
1. **`HeuristicDecisionEngine`**: Motor determinístico com calibração probabilística (<1ms);
2. **`ONNXNLIDecisionEngine`**: Motor de inferência de linguagem natural executado localmente via ONNX Runtime a partir de SLMs quantizados (Qwen2.5-0.5B);
3. **`OutlinesDecisionEngine`**: Decodificação restrita por autômatos finitos (FSM) com garantias estruturais.

Até então, o framework não dispunha de um mecanismo científico, padronizado e automatizado para comparar objetivamente:
- **Latência granular**: Percentis P50, P95, P99, média, mínimo e máximo;
- **Throughput**: Capacidade de processamento em requisições por segundo (RPS);
- **Acurácia**: Taxa de acerto global e por modo de operação (`route`, `risk`, `commit`, `skip`) contra os datasets de referência.

A proposta **IMP-0015** foi formulada para introduzir um harness completo de benchmark capaz de fornecer evidências empíricas e scorecard reprodutível de performance.

## Decisão de Arquitetura

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `EngineLatencyStats`: Contrato tipado para métricas de temporização (`p50_ms`, `p95_ms`, `p99_ms`, `mean_ms`, `min_ms`, `max_ms`).
   - `EngineBenchmarkResult`: Resultados por motor contendo acurácia percentual, estatísticas de latência, throughput RPS e distribuição de precisão por modo.
   - `BenchmarkReport`: Relatório consolidado com timestamp ISO, caminho do dataset, total de amostras e iterações, mapa de motores, determinação dos vencedores (`winner_latency`, `winner_accuracy`) e recomendações estratégicas.

2. **Cálculo de Percentis & Estatísticas (`calculate_latency_stats`)**:
   - Algoritmo de interpolação linear determinístico para cálculo de P50, P95 e P99 com precisão monotônica (`time.perf_counter`).
   - Cálculo de throughput baseado no tempo total de batch para medições realistas de saturação.

3. **Motor de Benchmark Autônomo (`SystemOneBenchmark`)**:
   - Suporte a datasets customizados em JSONL com fallback automático para amostras canônicas corporativas;
   - Fase preliminar de aquecimento (*warmup*) configurável para eliminar ruídos de JIT, I/O e inicialização;
   - Avaliação por categoria inteligente (`route`, `commit`, `risk`, `skip`);
   - Resiliência com fallback transparente caso bibliotecas opcionais não estejam presentes;
   - Geração de recomendações contextuais baseadas nos resultados observados.

4. **Interface CLI de Primeira Classe (`src/corporate_engineer/cli.py`)**:
   - Novo subcomando `corporate-engineer benchmark` suportando flags `--dataset`, `--engines`, `--iterations`, `--max-samples`, `--warmup`, `--format [text|json|markdown]` e `--output`.

## Consequências
- **Positivas**:
  - Evidências científicas e mensuráveis sobre qual motor utilizar em cada cenário da arquitetura (ex.: Heurístico para decisões de alta frequência sub-1ms na DAG, ONNX para grounded context com privacidade local total).
  - Scorecard reproduzível que permite detectar regressões de desempenho a cada novo modelo ou peso fine-tuned.
  - Zero dependência externa de serviços pagos ou APIs de terceiros.
- **Mitigações**:
  - Para evitar distorções em CPUs corporativas com carga variável, o benchmark calcula percentis P50/P95 e disponibiliza aquecimento prévio.
