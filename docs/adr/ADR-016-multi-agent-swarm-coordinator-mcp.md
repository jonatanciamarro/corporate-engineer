# ADR-016: Multi-Agent Swarm Coordinator via MCP Enterprise Hub

## Status
Aceito (Accepted)

## Data
2026-11-22

## Contexto & Motivação
O framework `corporate-engineer` estabeleceu um catálogo canônico de 8 subagentes especializados (`architect`, `tdd-guide`, `security-reviewer`, `code-reviewer`, `python-reviewer`, `build-error-resolver`, `refactor-cleaner` e `rag-pipeline-reviewer`) e implementou o `MCPEnterpriseHub` (IMP-0011) para gerenciar pools de ferramentas de múltiplos servidores MCP com Circuit Breakers e poda semântica via Sistema 1.

No entanto, a orquestração do framework operava essencialmente de forma sequencial na máquina de estados finitos (FSM) ou em tarefas pontuais isoladas. Para resolver problemas corporativos complexos em larga escala, era necessária uma camada de coordenação distribuída em enxame (*Swarm Coordinator*) capaz de:
1. Despachar sub-tarefas concorrentes em paralelo (*Fan-Out*);
2. Alocar para cada membro do enxame apenas as ferramentas MCP pertinentes ao seu papel com circuit breaker isolado;
3. Aguardar a convergência das tarefas com barreira de sincronização (*Fan-In*);
4. Agregar pareceres multi-perspectiva para formação de consenso deliberativo (ex.: revisão tripartite entre arquitetura, segurança e código).

A proposta **IMP-0016** foi concebida para fornecer essa capacidade de engenharia em enxame.

## Decisão de Arquitetura

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `SwarmMember`: Contrato para membros ativos do enxame contendo `agent_id`, `role`, `task_prompt`, `allowed_tools` e `status` (`IDLE`, `WORKING`, `COMPLETED`, `FAILED`).
   - `SwarmTaskResult`: Resultado individual de execução com `agent_id`, `role`, `output`, `success`, `execution_time_ms`, `tools_called` e `error`.
   - `SwarmGoalReport`: Relatório consolidado com `goal`, `swarm_name`, `total_agents`, `successful_tasks`, `failed_tasks`, `aggregated_consensus`, `results`, `execution_time_ms` e `recommendations`.

2. **Motor Swarm Coordinator (`src/corporate_engineer/orchestrator/swarm.py`)**:
   - Classe `SwarmCoordinator` integrada ao `MCPEnterpriseHub` e `SystemOneRouter`.
   - Método `create_swarm`: instancia membros atribuindo apenas ferramentas MCP filtradas por poda do Sistema 1 (`prune_tools_for_prompt`).
   - Método `dispatch_task`: executa o trabalho especializado de cada subagente com contenção por Circuit Breaker individual (falha em ferramenta externa não propaga e não derruba o agente nem o enxame).
   - Método `run_fan_out`: orquestração concorrente via `ThreadPoolExecutor` com barreira de sincronização (*Fan-In*) e sumário de execução.
   - Método `run_consensus`: revisão multi-agente concorrente sintetizando deliberação unificada (ex.: `APPROVED` ou `REJECTED`) a partir de múltiplos papéis avaliadores.

3. **CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Subcomando de primeira classe `corporate-engineer swarm` com suporte a `--goal`, `--roles`, `--mode [fanout|consensus]`, `--target`, `--workers`, `--format [text|json|markdown]` e `--output`.

## Consequências
- **Positivas**:
  - Paralelismo real e redução drástica do tempo de ciclo em revisões complexas e tarefas de engenharia distribuída (ex.: 3 agentes executam em ~6-60ms).
  - Isolamento rigoroso de falhas: circuit breakers individuais por servidor MCP protegem o enxame contra instabilidades de rede ou ferramentas quebradas.
  - Poda seletiva de contexto pelo Sistema 1, minimizando o consumo de tokens e a poluição do action space de cada subagente.
  - Consenso multi-perspectiva transparente e auditável.
- **Mitigações**:
  - Pool de threads parametrizado via `--workers` (default: 4) para evitar sobrecarga de CPU em máquinas locais.
  - Tratamento defensivo em todas as invocações de ferramentas remotas.
