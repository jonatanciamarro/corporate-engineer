# ADR-003: Exportação de Diagramas Mermaid Dinâmicos a partir da CLI `dag` (IMP-0005)

> **Status**: ACEITO (ACCEPTED)  
> **Data**: 2026-11-19  
> **Decisores**: Chief Orchestrator Architect, Antigravity AI  
> **Contexto Técnico**: Evolução das capacidades de observabilidade e documentação visual do grafo FSM e checkpoints de execução do `corporate-engineer`.

---

## 1. Contexto & Problema

O comando `corporate-engineer dag` foi introduzido para permitir a inspeção do ciclo de vida determinístico da máquina de estados finitos (FSM: `PLANNING` → `TDD` → `IMPLEMENT` → `AUDIT` → `DELIVER`) e listagem de checkpoints de recuperação.

No entanto, as saídas eram limitadas a listagens de texto tabular ou dumps JSON brutos. Desenvolvedores, arquitetos e documentadores não dispunham de uma forma automatizada de exportar representações visuais legíveis diretamente para documentações, ADRs, pull requests e relatórios executivos em formato Mermaid (Gfm).

---

## 2. Decisão Arquitetural

Decidiu-se implementar a proposta `IMP-0005` estendendo `AutonomousEngineeringGraph` e o subcomando `dag` da CLI:

1. **Métodos Nativos de Serialização Mermaid no Grafo (`graph.py`)**:
   - `fsm_to_mermaid(highlight_phase: str | None = None) -> str`: Produz a topologia declarativa da FSM no formato `flowchart TD` com suporte a destaque visual do nó correspondente a uma fase específica.
   - `to_mermaid(highlight_current: bool = False) -> str`: Método de instância que renderiza o estado ativo da instância atual.
   - `checkpoints_to_mermaid(checkpoints: list[dict[str, Any]]) -> str`: Constrói dinamicamente uma timeline cronológica (`flowchart LR`) com nós detalhando cada checkpoint persistido (`ticket_id`, `filename`, `phase`, `iteration_count`).

2. **Novos Argumentos na CLI (`cli.py`)**:
   - `--mermaid`: Flag booleana que instrui o comando `dag` a emitir saída em sintaxe Mermaid (`flowchart TD` para FSM ou `flowchart LR` quando combinado com `--checkpoints`).
   - `--output`: Argumento opcional para salvar diretamente o diagrama ou relatório gerado em um arquivo de destino (`.mmd`, `.md`, `.json`, etc.).

---

## 3. Matriz de Trade-offs & Alternativas Consideradas

| Critério | Opção A: Gerador Externo Baseado em Graphviz | Opção B: Diagramas Manuais em Markdown | Opção C: Métodos Embutidos Mermaid na Engine (Escolhida) |
|---|---|---|---|
| **Dependências Externas** | Ruim (exige binário do Graphviz instalado no SO). | Nenhuma. | **Zero dependências externas** (Gera Mermaid textual nativo). |
| **Renderização em GitHub/IDEs** | Exige conversão para imagem (.png/.svg). | Manual e propensa a desatualização. | **Renderização nativa instantânea** em GitHub, VS Code e Antigravity. |
| **Manutenibilidade** | Média. | Baixa (drift constante entre código e docs). | **Determinística**: O código é a fonte única da verdade para a FSM. |

---

## 4. Análise de Segurança & Blast Radius (STRIDE)

- **Input Validation**: Argumentos de caminho via `--output` são normalizados com `Path.resolve()` e garantem criação segura de diretórios pais (`mkdir(parents=True, exist_ok=True)`).
- **Zero Injeção de Código**: A formatação do Mermaid utiliza sanitização de caracteres em labels (`<br/>`, aspas escapadas).
- **Isolamento de Erros**: O exportador lida graciosamente com listas vazias de checkpoints emitindo um diagrama válido de nó vazio informativo.

---

## 5. Critérios de Aceite & Validação

- 100% dos testes unitários e de integração verdes (`test_cli_dag_mermaid`, `test_cli_dag_mermaid_output_file`, `test_cli_dag_checkpoints_mermaid`, `test_graph_fsm_to_mermaid`, etc.).
- Validação no pre-flight com 0 erros no Ruff, 0 erros no Mypy e 0 vazamentos de segredos.
