---
name: corp-pipeline
description: >-
  Corporate 5-Phase Engineering Pipeline for enterprise environments. Enforces Scope Alignment
  via grill-me_v2 & plan_v2, Shift-Left TDD, Surgical Implementation with 3-trial auto-debug,
  Pre-Flight Quality Gates, and Compliant Git Branching/PR generation.
---

# Corporate 5-Phase Engineering Pipeline (`corp-pipeline`)

This skill automates and governs the software delivery lifecycle for corporate and enterprise environments, ensuring strict quality standards, branch protection, Shift-Left TDD, and team-friendly Pull Requests.

---

## 🎯 When to Activate
- Automatically activated via the `/corp-pipeline` slash command.
- Activated whenever implementing enterprise features, bug fixes, or refactoring subject to corporate compliance, branch protection, or team code review.

---

## 🧭 The 5 Deterministic Phases

```text
[Input: Ticket/Demand]
       │
       ▼
[FASE 1: Governança, Contratos & Escopo] ────► 🔴 GATE 1: Aprovação Humana
  ├─ 1.1: /grill-me_v2 (Adaptativo: Entrevista & ADR em docs/adr/)
  └─ 1.2: /plan_v2 (Trade-off Matrix, STRIDE, Rollback & DTOs)
       │
       ▼ (Aprovado)
[FASE 2: Shift-Left TDD] ────────────────────► Testes falhando (RED)
       │
       ▼
[FASE 3: Implementação Cirúrgica] ───────────► Testes passando (GREEN) (Máx 3 retentativas)
       │
       ▼
[FASE 4: Pre-Flight Gate & Auditoria] ───────► Linter + Typecheck + Secret Scan
       │
       ▼
[FASE 5: Entrega Corporativa] ───────────────► 🔴 GATE 2: Aprovação Final ──► Branch & PR
```

---

## 🔹 Fase 1: Governança, Contratos & Escopo (Gate 1)

A Fase 1 orquestra nativamente as skills **`/grill-me_v2`** e **`/plan_v2`** antes de qualquer linha de teste ou código de produção ser escrita:

### 1.1. Refinamento de Requisitos & Síntese de ADR (via `/grill-me_v2`)
- **Modo Adaptativo**:
  - **Nova Feature / Mudança Arquitetural / Escopo Ambíguo**: Executa obrigatoriamente a entrevista investigativa do `/grill-me_v2` via `ask_question` (uma pergunta por vez com opção recomendada).
  - Extrai requisitos não-funcionais (SLAs de latência, throughput, tolerância a falhas e telemetria).
  - **Geração Automática de ADR**: Ao concluir o alinhamento, gera e versiona o arquivo formal em `docs/adr/ADR-<NUM>-<slug>.md` utilizando o template corporativo.
  - **Bugfix Pontual / Escopo 100% Fechado**: A entrevista pode ser dispensada, registrando-se um ADR sucinto ou pulando direto para o planejamento da sub-fase 1.2.

### 1.2. Planejamento Técnico & Contratos Formais (via `/plan_v2`)
- Consome o ADR gerado e consolida o artefato de plano contendo:
  - **Matriz de Trade-offs**: Comparativo entre no mínimo duas abordagens técnicas (latência, custo, complexidade, acoplamento).
  - **Modelagem de Ameaças (STRIDE / OWASP)**: Verificação de autenticação, integridade, autorização e segredos.
  - **Estratégia de Rollback & Análise de Blast Radius**: Procedimento explícito de reversão sem downtime.
  - **Contratos DTOs Formais**: Definição prévia e tipada de schemas e interfaces (Pydantic, TypeScript, Go structs).
  - O plano é gerado como um Artefato interativo no chat com `RequestFeedback: true`.

### 1.3. 🔴 GATE 1 (Confirmação Obrigatória)
- Apresente ao usuário o link do ADR gerado e o Plano Técnico emitido.
- **PARE e aguarde a confirmação explícita (`proceed` / `sim`) antes de avançar para a Fase 2.**

---

## 🔹 Fase 2: Shift-Left TDD (Contratos em Código)

1. **Detecção de Stack**:
   - Execute o detector automatizado:
     ```powershell
     python .agents/skills/corp-pipeline/scripts/stack_detector.py
     ```
   - Obtém `test_cmd`, `lint_cmd` e `typecheck_cmd`.
2. **Escrever Testes Automatizados**:
   - Crie testes unitários e de integração baseados estritamente nos contratos validados na Fase 1.
3. **Certificação RED**:
   - Execute o `test_cmd`.
   - **Assegure que os testes falham pelo motivo esperado antes de prosseguir.**

---

## 🔹 Fase 3: Implementação Cirúrgica & Auto-recuperação

1. **Implementação Mínima**:
   - Escreva apenas o código de produção estritamente necessário para satisfazer os testes da Fase 2.
2. **Execução de Testes (GREEN)**:
   - Execute o `test_cmd`.
3. **Auto-recuperação Cirúrgica (Teto: 3 tentativas)**:
   - Se o teste falhar, analise o traceback isolado e aplique correções cirúrgicas:
     - **Tentativa 1**: Correção de lógica interna ou imports.
     - **Tentativa 2**: Ajuste de tipagem ou contrato de mocks.
     - **Tentativa 3**: Ajuste fino final de runtime.
   - **Se persistir após a 3ª tentativa**: Interrompa imediatamente, exiba o diagnóstico exato e solicite orientação do usuário.

---

## 🔹 Fase 4: Pre-Flight Gate & Auditoria Local

Execute a suíte de conformidade corporativa:
1. **Linter**: Execute o `lint_cmd` detectado (ex: `ruff check .` ou `eslint .`).
2. **Typecheck**: Execute o `typecheck_cmd` detectado (ex: `mypy .` ou `tsc --noEmit`).
3. **Secret Scan**: Execute o scanner de credenciais:
   ```powershell
   python .agents/skills/corp-pipeline/scripts/secret_scanner.py .
   ```
4. **Regressão Global**: Execute a suíte completa de testes do projeto para garantir zero regressões.

---

## 🔹 Fase 5: Entrega Corporativa (Gate 2)

1. **🔴 GATE 2 (Confirmação Final)**:
   - Apresente o diff resumido, status de todos os testes e proposta de mensagem de commit semântico.
   - Aguarde o `proceed` do usuário.
2. **Branching & Git Governance**:
   - Verifique a branch atual: **NUNCA realize push ou commits diretos na `main` ou `master`**.
   - Crie branch de feature:
     ```bash
     git checkout -b feat/<TICKET_ID>-<slug>
     ```
3. **Commits Semânticos**:
   - Realize commits atômicos no padrão Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`).
4. **Geração de Pull Request**:
   - Gere o resumo do PR preenchido com o template em `.agents/skills/corp-pipeline/templates/pr_template.md`.
   - Se o GitHub CLI (`gh`) estiver disponível, sugira ou dispare `gh pr create`. Caso contrário, forneça o markdown completo pronto para abertura na interface web corporativa.
