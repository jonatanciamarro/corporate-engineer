# ADR-014: Safe Storage Optimizer & Automated Disk Hygiene System

## Status
Aceito (Accepted)

## Data
2026-11-22

## Contexto & Motivação
Em ambientes de desenvolvimento de software com agentes autônomos e execução contínua de pipelines (compilação de artefatos, downloads de modelos ONNX/GGUF, caches de pacotes `pip`/`npm`, e checkpoints de inferência de ML), o volume de armazenamento em disco da estação de trabalho local pode atingir rapidamente limites críticos (ex.: partição `C:` reduzida a menos de 100 MB).

No incidente registrado nesta sessão, a partição principal `C:` atingiu um ponto crítico de exaustão com apenas 64 MB de espaço livre, o que afeta drasticamente a estabilidade do sistema operacional, memória virtual (`pagefile.sys`), subprocessos e execução de suítes de testes.

Identificou-se que a maior parte do espaço consumido provém de:
1. Fragmentos e downloads parciais órfãos (`*-partial*` do Ollama e `*.th.partial` do Torch hub);
2. Caches redundantes de gerenciadores de dependências (`pip cache` com >4.5 GB e `npm-cache` com >2.8 GB);
3. Modelos volumosos locais e checkpoints sem uso ativo (como pesos GGUF de 3.5 GB em GPT4All e modelos descontinuados de 5.2 GB em Ollama);
4. Caches massivos de streaming e áudio offline (como o cache binário de áudio do Spotify em `AppData\Local\Spotify\Data` com >2.1 GB);
5. Caches transitivos de temporários do sistema e usuário (`%TEMP%`, `CrashDumps`).

Até o momento, a limpeza do disco exigia scripts ad-hoc ou intervenções manuais propensas a erro, com risco de exclusão acidental de dados pessoais importantes. Faz-se necessário um módulo nativo corporativo, seguro, automatizado e governado pelo Corp-Pipeline.

## Decisão de Arquitetura

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `StorageTarget`: Representa um alvo identificável de limpeza (`category`, `name`, `path`, `size_bytes`, `is_safe`, `description`).
   - `StorageCleanResult`: Registra o resultado da tentativa de limpeza de um alvo (`target_name`, `path`, `freed_bytes`, `success`, `error`).
   - `StorageOptimizationReport`: DTO consolidado contendo `total_freed_bytes`, `total_freed_gb`, `results: list[StorageCleanResult]` e `dry_run: bool`.

2. **Motor de Higiene e Otimização de Armazenamento (`src/corporate_engineer/quality/storage_cleaner.py`)**:
   - Classe `SafeStorageCleaner`:
     - **Invariante de Preservação Pessoal (Allowlist / Denylist estrita)**: Proibição estrita de tocar em diretórios de dados do usuário (`Documents`, `Desktop`, `Pictures`, `Videos`, `Music`, e códigos do repositório).
     - **Suporte a Alvos Seguros**: Limpeza de caches de desenvolvimento (`pip`, `npm`, `torch`, `huggingface`, `%TEMP%`, `CrashDumps`).
     - **Suporte a Alvos de Modelos Pesados**: Remoção seletiva e segura de pesos de modelos locais explicitamente aprovados (como `WizardLM-7B-uncensored.Q4_0.gguf` no GPT4All e modelos órfãos no Ollama) e cache binário de streaming do Spotify.
     - **Simulação com `--dry-run`**: Permite auditar exatamente quantos bytes serão liberados sem alterar nenhum arquivo em disco.
     - **Tolerância a Falhas**: Falha ao remover um arquivo em uso (ex.: bloqueado pelo sistema operacional) não interrompe o ciclo dos demais alvos, reportando `error` de forma limpa.

3. **Integração na CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Subcomando `corporate-engineer clean`:
     - `--dry-run`: Diagnostica os alvos e projeta o espaço a ser liberado em JSON/Texto.
     - `--target <category|all>`: Filtra alvos por categoria (`caches`, `models`, `temp`, `all`).
     - `--format [text|json]`: Saída para humanos ou ingestão em dashboards de observabilidade.

## Consequências
- **Positivas**:
  - Recuperação imediata de até 20+ GB de armazenamento no disco principal de forma auditável e determinística.
  - Prevenção de crashes do sistema operacional decorrentes de falta de espaço em disco.
  - 100% de conformidade com os princípios corporativos de imutabilidade e integridade de arquivos pessoais do usuário.
- **Mitigações**:
  - Todo caminho alvo passa por validação estrita de caminho canônico (`Path.resolve()`) para impedir ataques de path traversal ou exclusões forasteiras.
  - Inclusão do modo `--dry-run` como padrão defensivo para conferência prévia.
