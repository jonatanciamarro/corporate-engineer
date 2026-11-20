# ADR-004: Motor Nativo de Mutation Testing via AST para Validação de Testes AI (IMP-0006)

> **Status**: ACEITO (ACCEPTED)  
> **Data**: 2026-11-20  
> **Decisores**: Chief Orchestrator Architect, Antigravity AI  
> **Contexto Técnico**: Introdução de testes de mutação no pipeline de engenharia corporativa com agentes autônomos de IA.

---

## 1. Contexto & Problema

Com a proliferação de código e testes gerados automaticamente por modelos de linguagem (LLMs), a métrica tradicional de **cobertura de linhas (Line Coverage)** revelou-se insuficiente para certificar a qualidade do software. Conforme documentado no relatório *Deep Research em Engenharia de Software por IA (Novembro 2026)*, testes gerados por IA frequentemente alcançam altas taxas de cobertura executando código sem exercer assertividade sobre a lógica de negócios, criando uma falsa sensação de segurança.

Havia a necessidade de um **motor de testes de mutação (Mutation Testing)** nativo, rápido e integrado à CLI corporativa, capaz de validar empiricamente se os testes são capazes de detectar falhas lógicas induzidas.

---

## 2. Decisão Arquitetural

Decidiu-se implementar a proposta `IMP-0006` através de um motor de mutação baseado puramente na árvore de sintaxe abstrata (`ast`) do Python, sem depender de ferramentas pesadas de terceiros:

1. **Varredura e Mutação AST (`src/corporate_engineer/quality/mutation.py`)**:
   - `scan_mutation_points(source_code)`: Analisa o AST e identifica operadores relacionais (`==`, `!=`, `<`, `<=`, `>`, `>=`), binários aritméticos (`+`, `-`, `*`, `//`) e constantes booleanas (`True`, `False`).
   - `apply_mutation(source_code, point)`: Emprega `ast.NodeTransformer` isolado para aplicar uma única mutação por mutante gerado e recompõe o código via `ast.unparse`.
   - `ASTMutationEngine`: Orquestra a execução da suíte de testes contra cada mutante em subprocesso isolado, calculando a métrica formal de **Mutation Score**:
     $$\text{Mutation Score} = \left(\frac{\text{Mutantes Mortos}}{\text{Total de Mutantes}}\right) \times 100$$

2. **Integração com a CLI (`cli.py`)**:
   - Flags `--mutation`, `--target-file` e `--max-mutants` no subcomando `corporate-engineer audit`.
   - Suporte a relatório em console formatado e exportação JSON estruturada.

3. **Garantia de Integridade**:
   - O código original do arquivo alvo é preservado em memória e obrigatoriamente restaurado em bloco `finally`, prevenindo qualquer corrupção acidental da base de código.

---

## 3. Matriz de Trade-offs & Alternativas Consideradas

| Critério | Opção A: Mutmut (Ferramenta Externa CLI) | Opção B: Cosy/Stryker via Docker | Opção C: Motor AST Nativo Embutido (Escolhida) |
|---|---|---|---|
| **Dependências Externas** | Média (dependência PyPI pesada). | Alta (requer daemon Docker). | **Zero dependências extras** (Usa biblioteca padrão `ast`). |
| **Integração no Pipeline** | Exige orquestração via subprocess shell. | Complexa. | **Nativa**: Integrado à CLI `audit` e ao Quality Gate. |
| **Velocidade & Amostragem**| Varre todos os arquivos (horas em repos grandes). | Lenta. | **Cirúrgica**: Amostragem controlada via `--max-mutants`. |
| **Segurança e Rollback** | Pode deixar arquivos corrompidos se abortado. | Isolado em container. | **Determinístico**: Bloco `finally` garante restauração imediata. |

---

## 4. Análise de Segurança & Blast Radius (STRIDE)

- **Tampering**: A restauração em bloco `try ... finally` garante que arquivos fonte nunca permaneçam mutados em caso de falha de teste, interrupção de teclado ou timeout.
- **Denial of Service (DoS)**: Timeout configurável por mutante (`timeout_seconds=15.0`) trata loops infinitos induzidos pela mutação classificando o mutante como morto (`KILLED`) sem congelar o pipeline.
- **Information Disclosure**: Saída do auditor sanitiza caminhos e exibe apenas metadados dos mutantes.

---

## 5. Critérios de Aceite & Validação

- Testes dedicados em `tests/test_mutation.py` validando identificação de mutantes, transformação AST, cálculo do mutation score e integração com a CLI.
- 100% de aprovação na suíte de testes (74/74 PASS) com 91% de cobertura global.
