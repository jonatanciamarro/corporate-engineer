# ADR-017: GitHub Actions Workflow de Auto-Remediação em PRs (self-heal.yml)

## Status
Aceito (Accepted)

## Data
2026-11-22

## Contexto & Motivação
O framework `corporate-engineer` implementou o motor `ASTSelfHealingFixer` (`src/corporate_engineer/eval/fixer.py`) e o subcomando de primeira classe `corporate-engineer fix --auto` (IMP-0012), capazes de detectar e remediar deterministicamente violações estruturais em AST Python (como falta de anotação `-> None` em métodos `__init__`, argumentos padrão mutáveis como listas/dicionários, e declarações `pass` redundantes com docstrings).

Entretanto, esse mecanismo dependia exclusivamente da execução manual pelos engenheiros em seus ambientes locais. Em equipes distribuídas ou fluxos contínuos de PRs, violações triviais frequentemente chegavam aos Pull Requests no GitHub, gerando falhas nos portões de qualidade ou exigindo idas e vindas de code review para correções sintáticas básicas.

A iniciativa **IMP-0017** foi concebida para automatizar essa auto-cura diretamente no ciclo de integração contínua (CI) do GitHub Actions, assegurando que todo PR submetido receba correções imediatas de forma autônoma e segura.

## Decisão de Arquitetura

1. **Workflow Declarativo do GitHub Actions (`.github/workflows/self-heal.yml`)**:
   - Acionamento restrito a eventos de Pull Request: `opened`, `synchronize` e `reopened` direcionados à branch `main`.
   - Permissões mínimas de privilégio (`permissions`):
     - `contents: write`: necessária para commit e push das correções na branch do PR.
     - `pull-requests: write`: para anotações e feedback automatizado no PR.

2. **Passos de Execução do Pipeline**:
   - **Checkout**: `actions/checkout@v4` com `ref: ${{ github.head_ref }}` e histórico completo (`fetch-depth: 0`).
   - **Setup Python**: `actions/setup-python@v5` configurado para Python 3.11 com cache de pacotes via pip.
   - **Instalação**: Instalação das dependências corporativas de qualidade (`ruff`, `mypy`, `pytest-cov`) e instalação em modo editável (`pip install -e ".[dev,test]"`).
   - **Remediação AST**: Execução do comando oficial `corporate-engineer fix --auto --path src/`.
   - **Commit & Push Condicional**:
     - Inspeção de alterações via `git status --porcelain src/`.
     - Caso haja arquivos modificados, commit assinado como `github-actions[bot]`.
     - Inclusão do trailer `[skip ci]` na mensagem de commit (`chore(self-heal): apply automated AST fixes [skip ci]`) e push imediato para o branch de origem do PR.
   - **Auditoria de Qualidade Estrita**: Execução de `corporate-engineer audit --strict` para validação de 0 erros em testes, linter, tipos e segredos.

3. **Mitigação de Loops Infinitos de CI**:
   - O uso do `GITHUB_TOKEN` nativo por padrão não re-dispara eventos `pull_request` no GitHub Actions.
   - A inclusão explícita de `[skip ci]` no corpo do commit fornece uma segunda camada de defesa em profundidade, prevenindo acionamentos recursivos em outros runners ou ferramentas de CI externas.

## Consequências

- **Positivas**:
  - Eliminação de fricção em revisões humanas para problemas sintáticos triviais.
  - Correção instantânea e transparente diretamente na branch do colaborador antes do merge.
  - Conformidade estrita garantida por `corporate-engineer audit --strict` antes de qualquer liberação.
- **Mitigações**:
  - Escopo de auto-cura restrito estritamente a `src/`, evitando alterações acidentais em configurações ou testes.
  - Apenas transformadores de AST determinísticos e testados são autorizados a aplicar alterações.
