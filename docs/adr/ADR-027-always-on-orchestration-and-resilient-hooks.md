# ADR-027: Resiliência Universal de Hooks do Ciclo de Vida e Ativação Permanente de Regras Always-On (IMP-0028)

## Status
Aceito (Accepted)

## Data
2026-11-24

## Contexto & Motivação
Durante o uso contínuo do framework `corporate-engineer`, identificou-se uma degradação de experiência onde o assistente de IA parecia "esquecer" regras corporativas, não executava hooks do ciclo de vida automaticamente e operava sem o uso pleno dos motores de metaprompting e antecipação proativa.

Uma auditoria investigativa minuciosa comprovou duas causas-raiz concretas:
1. **Falta de Frontmatter de Trigger**: O arquivo `.agents/rules/corp-pipeline-orchestrator.md` foi gravado sem o bloco YAML `trigger: always_on`. O mecanismo de descoberta do Antigravity ignora arquivos de regras que não possuem esse gatilho explícito, impedindo que o Master Orchestrator fosse injetado no prompt de sistema das sessões.
2. **Caminhos Relativos Quebrados em `hooks.json`**: O arquivo `.agents/hooks.json` configurava comandos na forma `python orchestration/hooks/session_start.py`. Como o Antigravity executa os processos de hook com CWD na raiz do workspace (`E:\projcts\corporate engineer`), o comando buscava uma pasta `orchestration` inexistente na raiz, lançando silenciosamente `[Errno 2] No such file or directory` em todos os eventos (`SessionStart`, `PreInvocation`, `PreToolUse`, `PostToolUse`, `Stop`).
3. **Ambiguidade de Interpretador Python no Windows**: O comando `python` invocado pelo `cmd /c` utilizava a versão global de sistema (Python 3.10) em vez do ambiente virtual isolado `.venv` (Python 3.11), arriscando incompatibilidades de pacotes e caminhos.

## Decisão de Arquitetura

1. **Ativação Always-On da Regra Mestra**:
   - Inserir no topo de `.agents/rules/corp-pipeline-orchestrator.md`:
     ```yaml
     ---
     trigger: always_on
     description: Master Protocol for Corp-Pipeline Chief Orchestrator and 6-Phase Engineering Lifecycle.
     ---
     ```
   - Garantir que todas as regras no diretório `.agents/rules/` possuam gatilhos formais válidos e testados.

2. **Criação do Dispatcher Universal de Hooks (`run_hook.py`)**:
   - Implementar `.agents/orchestration/hooks/run_hook.py` com as seguintes responsabilidades:
     - Detecção inteligente do interpretador `.venv`: busca prioritária em `.venv/Scripts/python.exe` (Windows) ou `.venv/bin/python` (POSIX), com fallback gracioso para `sys.executable`.
     - Resolução agnóstica de caminhos: localiza o hook correto independentemente de ser disparado a partir da raiz do repositório ou de dentro de `.agents`.
     - Injeção de `src/` em `sys.path` antes da execução de qualquer lógica de negócio.
     - Captura e formatação segura de erros em `stderr` para evitar bloqueios cegos de stdin/stdout.

3. **Atualização Padronizada de `.agents/hooks.json`**:
   - Mapear todos os 5 eventos do ciclo de vida utilizando caminhos ancorados a partir da raiz:
     - `SessionStart`: `python .agents/orchestration/hooks/run_hook.py session_start`
     - `PreInvocation`: `python .agents/orchestration/hooks/run_hook.py proactive_advisor`
     - `PreToolUse`: `python .agents/orchestration/hooks/run_hook.py pre_tool_security_guard`
     - `PostToolUse`: `python .agents/orchestration/hooks/run_hook.py post_tool_auto_healer`
     - `Stop`: `python .agents/orchestration/hooks/run_hook.py session_turnover_gate`

4. **Garantia de Shift-Left TDD**:
   - Criação de suíte de testes unitários em `tests/test_hook_resilience_and_rule_triggers.py` garantindo que todos os arquivos `.md` em `.agents/rules/` possuam triggers válidos e que o launcher execute com sucesso a partir de múltiplos diretórios de trabalho.

## Consequências

### Positivas:
- **Zero Amnésia**: O Master Orchestrator estará presente em 100% dos turnos e sessões como regra `always_on`.
- **Automação E2E**: Todos os hooks (`PreInvocation`, `PreToolUse`, `PostToolUse`, etc.) voltam a disparar com precisão cirúrgica.
- **Potência Máxima**: Todo prompt passa a receber a antecipação proativa de 2 passos e refinamento de metaprompt estruturado automaticamente.
- **Resiliência Multiplataforma**: Zero dependência de diretório de trabalho ou de configuração manual de PATH do sistema operacional.

### Trade-offs:
- Pequena sobrecarga de alguns milissegundos na chamada do despachante universal `run_hook.py`, amplamente compensada pela confiabilidade e isolamento de erros.
