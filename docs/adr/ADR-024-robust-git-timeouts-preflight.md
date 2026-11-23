# ADR-024: Tratamento Robusto de Timeouts Git e Eliminação de Erros Silenciosos no Pre-Flight

## Status
Aceito (Accepted)

## Data
2026-11-22

## Contexto & Motivação
A auditoria técnica profunda realizada no ecossistema `corporate-engineer` via Swarm (`relatorio_auditoria_swarm.md`) revelou três fontes críticas de erros silenciosos e fragilidades em operações de infraestrutura e qualidade:
1. **Timeouts Agressivos e Falhas Mascaradas em `git_utils.py`**:
   Operações remotas essenciais como `is_branch_pushed` (`git ls-remote`) e `push_branch_to_remote` (`git push`) possuíam limites estáticos de 2.0s a 3.0s, insuficientes para ambientes com latência de rede corporativa, túneis VPN ou conexões lentas. Em caso de estouro de tempo ou falha de conectividade, exceções `(OSError, subprocess.SubprocessError)` eram capturadas genericamente e retornavam silenciosamente `False`, fazendo o pipeline presumir erroneamente que branches inexistem ou que o push falhou sem qualquer detalhe de diagnóstico.
2. **Supressão Silenciosa de Exceções Git no `surgical_runner.py`**:
   No método `collect_changed_files`, comandos como `git status --porcelain` e `git diff` engoliam erros de subprocesso através de blocos `except (subprocess.SubprocessError, OSError): pass`. Na ocorrência de conflitos de lock (`.git/index.lock`) ou ausência de Git no PATH, o runner cirúrgico simplesmente retornava uma lista vazia de arquivos alterados sem emitir nenhum aviso ao operador.
3. **Execução de Comandos com `shell=True` e Timeout Fixo em `quality/gate.py`**:
   O método `run_tests` no `QualityGateRunner` executava testes com `shell=True` e interpolação de strings (`f'"{sys.executable}" -m pytest'`), impondo riscos desnecessários de shell injection e suscetibilidade a divergências de escape no terminal. Além disso, o timeout de 120s era rígido e não permitia parametrização por suítes de maior porte, nem tratava explicitamente `subprocess.TimeoutExpired`.

A iniciativa **IMP-0022** implementa a eliminação estrutural de erros silenciosos, introduz timeouts configuráveis com logging detalhado via biblioteca padrão `logging` e migra a execução de testes para listas de argumentos seguros com `shell=False`.

## Decisão de Arquitetura

1. **Robustez e Diagnóstico em `src/corporate_engineer/git_utils.py`**:
   - Inclusão de `logger = logging.getLogger(__name__)`.
   - Adição de parâmetro `timeout: float = 15.0` (configurável via argumento ou variável de ambiente `CORP_GIT_TIMEOUT`).
   - Captura e registro explícito de `subprocess.TimeoutExpired` em `is_branch_pushed` e `push_branch_to_remote` com `logger.warning`.
   - Registro de alertas diagnósticos quando a resolução de remote URL falhar, em vez de mascarar silenciosamente o erro.

2. **Transparência e Resiliência em `src/corporate_engineer/quality/surgical_runner.py`**:
   - Substituição de blocos `pass` cegos por `logger.warning("Git subprocess error in %s: %s", cmd, exc)`.
   - Parametrização de timeout de 15.0s para inspeção de status e diffs.
   - Verificação de plataforma (`os.name == "nt"`) antes da seleção de `.venv/Scripts/pytest.exe` para portabilidade POSIX.

3. **Execução Segura com `shell=False` em `src/corporate_engineer/quality/gate.py`**:
   - Conversão de comandos string para listas de argumentos (`list[str]`) e execução estrita com `shell=False`.
   - Parâmetro configurável `timeout: float = 120.0`.
   - Tratamento especializado de `subprocess.TimeoutExpired` retornando `exit_code=-2` e `stderr=f"Test command timed out after {timeout}s"`.
   - Filtro de diretórios internos (`.git`, `.venv`, `.agents`, `__pycache__`) na varredura estática de código para otimização de I/O.

4. **Shift-Left TDD (`tests/test_git_robustness_and_silent_errors.py`)**:
   - Testes unitários com mocks de `subprocess.run` validando captura de `TimeoutExpired` e emissão de logs.
   - Testes de execução com `shell=False` e timeout customizado no QualityGate.
   - Testes de logging transparente em falhas do runner cirúrgico.

## Consequências

- **Positivas**:
  - Eliminação comprovada de falhas silenciosas em operações Git e Quality Gate.
  - Diagnósticos ricos e rastreabilidade imediata em logs de auditoria e CI/CD.
  - Segurança aprimorada eliminando `shell=True` na execução de testes.
  - Flexibilidade operacional com timeouts customizáveis para redes corporativas de alta latência.
- **Negativas / Riscos**:
  - Nenhuma quebra de retrocompatibilidade; todas as assinaturas mantêm valores padrão seguros.
