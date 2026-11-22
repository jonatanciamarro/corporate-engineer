# Pull Request: feat(system-one): Autonomous benchmark & evaluation harness (IMP-0015)

## 📋 Identificação da Demanda
- **Ticket / Issue**: `IMP-0015`
- **Tipo de Alteração**: `feat`
- **Escopo**: `system-one`
- **ADR Associado**: [ADR-015: Autonomous Benchmark & Evaluation Harness para Motores do Sistema 1](../adr/ADR-015-system-one-benchmark-eval-harness.md)

---

## 🎯 Resumo das Modificações

Implementação do **Autonomous Benchmark & Evaluation Harness (IMP-0015)** para medição, avaliação empírica e comparação quantitativa entre os motores de decisão do Sistema 1 (`Heuristic`, `ONNX Runtime` e `Outlines`):

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `EngineLatencyStats`: Contrato para estatísticas de latência com `p50_ms`, `p95_ms`, `p99_ms`, `mean_ms`, `min_ms`, `max_ms`.
   - `EngineBenchmarkResult`: Resultados por motor cobrindo acurácia, latência, throughput RPS, erros e acurácia por categoria (`route`, `risk`, `commit`, `skip`).
   - `BenchmarkReport`: Relatório estruturado de benchmark com timestamp ISO, dataset, iterações, mapa de motores, determinação de vencedores e recomendações contextuais.

2. **Cálculo de Percentis e Estatísticas (`src/corporate_engineer/system_one/benchmark.py`)**:
   - Função `calculate_latency_stats` com interpolação linear para cálculo determinístico de P50, P95 e P99.
   - Cálculo de throughput em requisições por segundo (RPS) com precisão monotônica.

3. **Motor de Benchmark Autônomo (`SystemOneBenchmark`)**:
   - Suporte a leitura de datasets JSONL com fallback automático para amostras canônicas corporativas.
   - Fase de aquecimento (*warmup*) configurável para eliminar interferências de JIT e I/O inicial.
   - Avaliação por categoria (`route`, `commit`, `risk`, `skip`).
   - Resiliência operacional com fallback transparente.
   - Geração de recomendações contextuais baseadas em evidências empíricas.

4. **CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Novo subcomando `corporate-engineer benchmark` suportando:
     - `--dataset`: caminho para dataset JSONL;
     - `--engines`: lista de motores a avaliar (`heuristic`, `onnx`, `outlines`);
     - `--iterations`: repetições sobre o dataset;
     - `--max-samples`: limite de amostras analisadas;
     - `--warmup`: iterações preliminares de aquecimento;
     - `--format`: visualizações em `text`, `json` ou `markdown`;
     - `--output`: exportação do relatório para arquivo.

5. **Suíte de Testes & Pre-Flight**:
   - 7 novos testes unitários e de integração em `tests/test_system_one_benchmark.py`.
   - Expansão da suíte para 162 testes automatizados (100% de aprovação e 87% de cobertura).

---

## 🧪 Evidências de Teste & Qualidade

```text
============================= test session starts =============================
platform win32 -- Python 3.10.6, pytest-9.2.0, pluggy-1.7.0
plugins: hypothesis-6.168.5, cov-7.1.0
collected 162 items

162 passed in 69.06s (Suíte 100% verde)
Coverage Global: 87%
Ruff Linter & Formatter: 0 erros / 95 arquivos formatados
Mypy Strict Type Check: Success: no issues found in 57 source files
Pre-Flight Secret Scanner: PASS (0 segredos ou credenciais expostas)
```

---

## 🚀 Como Testar Localmente

```bash
# Executar benchmark padrão (Heuristic vs ONNX) com 10 amostras
.venv\Scripts\python -m corporate_engineer.cli benchmark --max-samples 10

# Exportar relatório em Markdown
.venv\Scripts\python -m corporate_engineer.cli benchmark --format markdown --output benchmark_report.md

# Exportar relatório em JSON
.venv\Scripts\python -m corporate_engineer.cli benchmark --format json
```
