"""
Suíte de testes unitários e de integração para validação de scripts PowerShell de otimização Windows.
Cobre sintaxe AST do PowerShell, guardrails de privilégios de Administrador, parâmetro -WhatIf,
modo de restauração limpa e métricas de memória antes/depois.
"""

from __future__ import annotations

import base64
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS_DIR = Path("scripts")
TARGET_SCRIPTS = [
    "optimize_windows_for_ai_dev.ps1",
    "start_interview_mode.ps1",
    "stop_interview_mode.ps1",
]

ADMIN_PATTERNS = [
    re.compile(r"\[Security\.Principal\.WindowsPrincipal\]", re.IGNORECASE),
    re.compile(r"\[Security\.Principal\.WindowsBuiltInRole\]::Administrator", re.IGNORECASE),
    re.compile(r"#Requires\s+-RunAsAdministrator", re.IGNORECASE),
    re.compile(
        r"IsInRole\s*\(\s*\[Security\.Principal\.WindowsBuiltInRole\]::Administrator\s*\)",
        re.IGNORECASE,
    ),
    re.compile(r"Test-IsAdmin|Assert-Admin", re.IGNORECASE),
]

WHATIF_PATTERNS = [
    re.compile(
        r"\[CmdletBinding\([^)]*SupportsShouldProcess\s*=?\s*(?:\$true)?\s*[^)]*\)\]",
        re.IGNORECASE,
    ),
    re.compile(r"\$PSCmdlet\.ShouldProcess", re.IGNORECASE),
    re.compile(r"\[switch\]\s*\$WhatIf", re.IGNORECASE),
]

MEMORY_PATTERNS = [
    re.compile(r"Win32_OperatingSystem", re.IGNORECASE),
    re.compile(r"FreePhysicalMemory", re.IGNORECASE),
    re.compile(r"TotalVisibleMemorySize", re.IGNORECASE),
    re.compile(r"Get-Process", re.IGNORECASE),
    re.compile(r"\[System\.GC\]", re.IGNORECASE),
]


def _static_syntax_check(content: str) -> tuple[bool, list[str]]:
    """Verificação estática de sintaxe (parênteses, chaves e aspas) para ambientes sem PowerShell."""
    errors: list[str] = []
    stack: list[tuple[str, int]] = []
    pairs = {")": "(", "}": "{", "]": "["}

    in_single_quote = False
    in_double_quote = False
    escape = False

    for idx, char in enumerate(content, start=1):
        if escape:
            escape = False
            continue
        if char == "`":
            escape = True
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            continue
        if in_single_quote or in_double_quote:
            continue

        if char in "({[":
            stack.append((char, idx))
        elif char in ")}]":
            expected = pairs[char]
            if not stack or stack[-1][0] != expected:
                errors.append(f"Unmatched closing '{char}' at char {idx}")
            else:
                stack.pop()

    if in_single_quote:
        errors.append("Unclosed single quote")
    if in_double_quote:
        errors.append("Unclosed double quote")
    while stack:
        open_char, pos = stack.pop()
        errors.append(f"Unclosed '{open_char}' at char {pos}")

    return len(errors) == 0, errors


def validate_powershell_ast(script_path: Path) -> tuple[bool, list[str]]:
    """Valida a sintaxe AST de um script PowerShell usando o Parser nativo ou verificação estática."""
    if not script_path.exists():
        return False, [f"Arquivo {script_path} não encontrado"]

    powershell_bin = shutil.which("powershell") or shutil.which("pwsh")
    if powershell_bin:
        posix_path = script_path.resolve().as_posix()
        ps_code = f"""
        $errors = $null
        $tokens = $null
        $ast = [System.Management.Automation.Language.Parser]::ParseFile('{posix_path}', [ref]$tokens, [ref]$errors)
        if ($errors.Count -gt 0) {{
            $errors | ForEach-Object {{ Write-Output "$($_.Extent.StartLineNumber):$($_.Extent.StartColumnNumber) - $($_.Message)" }}
            exit 1
        }}
        exit 0
        """
        encoded_cmd = base64.b64encode(ps_code.encode("utf-16le")).decode("ascii")
        try:
            res = subprocess.run(
                [powershell_bin, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded_cmd],
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            error_lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            return res.returncode == 0, error_lines
        except (subprocess.TimeoutExpired, OSError) as e:
            return False, [f"Erro na execução do PowerShell: {e}"]

    content = script_path.read_text(encoding="utf-8", errors="ignore")
    return _static_syntax_check(content)


def has_admin_check(content: str) -> bool:
    """Verifica se o script contém verificação obrigatória de privilégios de Administrador."""
    return any(pattern.search(content) for pattern in ADMIN_PATTERNS)


def has_whatif_support(content: str) -> bool:
    """Verifica se o script suporta o parâmetro -WhatIf e ShouldProcess."""
    return any(pattern.search(content) for pattern in WHATIF_PATTERNS)


def has_memory_metrics(content: str) -> bool:
    """Verifica se o script coleta métricas de memória física (RAM)."""
    return any(pattern.search(content) for pattern in MEMORY_PATTERNS)


def has_clean_restoration_logic(script_name: str, content: str) -> bool:
    """Verifica se o script implementa modo de restauração limpa e reversibilidade."""
    has_error_handling = bool(re.search(r"try\s*\{.*\}\s*catch|trap", content, re.DOTALL))

    if "start_interview_mode" in script_name:
        # Deve persistir estado (JSON ou XML) e possuir tratamento de erro
        has_state_save = bool(
            re.search(r"ConvertTo-Json|Export-Clixml|\.interview_state|StateFile", content)
        )
        return has_state_save and has_error_handling

    if "stop_interview_mode" in script_name:
        # Deve restaurar serviços, ler o estado persistido e limpar o arquivo temporário
        has_state_load = bool(
            re.search(r"ConvertFrom-Json|Import-Clixml|\.interview_state|StateFile", content)
        )
        has_service_restore = bool(re.search(r"Start-Service|Set-Service", content))
        has_cleanup = bool(re.search(r"Remove-Item", content))
        return has_state_load and has_service_restore and has_cleanup

    if "optimize_windows_for_ai_dev" in script_name:
        # Deve possuir suporte a restauração/reversão (-Restore ou Backup) e tratamento de erro
        has_restore_support = bool(
            re.search(
                r"-Restore|Restore|Backup|Rollback|Revert",
                content,
                re.IGNORECASE,
            )
        )
        return has_restore_support and has_error_handling

    return has_error_handling


# ==============================================================================
# TESTES DE UNIDADE: MOTOR DE VALIDAÇÃO DE AST E GUARDRAILS
# ==============================================================================


def test_powershell_ast_validator_clean_code(tmp_path: Path) -> None:
    """Valida que código PowerShell com sintaxe perfeita passa com 0 erros."""
    valid_ps = tmp_path / "valid.ps1"
    valid_ps.write_text(
        '[CmdletBinding()]\nparam([string]$Name)\nWrite-Output "Hello $Name"\n',
        encoding="utf-8",
    )
    ok, errors = validate_powershell_ast(valid_ps)
    assert ok is True
    assert len(errors) == 0


def test_powershell_ast_validator_syntax_error(tmp_path: Path) -> None:
    """Valida que código PowerShell corrompido é detectado com erro descritivo."""
    invalid_ps = tmp_path / "invalid.ps1"
    invalid_ps.write_text(
        "function Test-Broken {\n    if ($true) {\n        Write-Output 'Unclosed'\n",
        encoding="utf-8",
    )
    ok, errors = validate_powershell_ast(invalid_ps)
    assert ok is False
    assert len(errors) > 0


def test_guardrail_admin_check_detection() -> None:
    """Valida detecção de guardrail de Administrador."""
    clean_snippet = """
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) { throw "Execute como Administrador!" }
    """
    assert has_admin_check(clean_snippet) is True

    requires_snippet = "#Requires -RunAsAdministrator\nWrite-Output 'Ok'"
    assert has_admin_check(requires_snippet) is True

    missing_snippet = "Write-Output 'No admin check here'"
    assert has_admin_check(missing_snippet) is False


def test_guardrail_whatif_support_detection() -> None:
    """Valida detecção de suporte a -WhatIf e SupportsShouldProcess."""
    valid_binding = """
    [CmdletBinding(SupportsShouldProcess = $true)]
    param()
    if ($PSCmdlet.ShouldProcess("Registry", "Tweak")) { Set-ItemProperty ... }
    """
    assert has_whatif_support(valid_binding) is True

    missing_binding = """
    [CmdletBinding()]
    param()
    Set-ItemProperty ...
    """
    assert has_whatif_support(missing_binding) is False


def test_guardrail_memory_metrics_detection() -> None:
    """Valida detecção de coleta de métricas de memória RAM."""
    valid_metric = """
    $os = Get-CimInstance Win32_OperatingSystem
    $freeRamMB = [Math]::Round($os.FreePhysicalMemory / 1024, 2)
    Write-Host "RAM Livre: $freeRamMB MB"
    """
    assert has_memory_metrics(valid_metric) is True

    missing_metric = "Write-Host 'No memory check'"
    assert has_memory_metrics(missing_metric) is False


def test_guardrail_clean_restoration_detection() -> None:
    """Valida regras de reversibilidade e restauração limpa para cada script."""
    # start_interview_mode
    start_valid = """
    try {
        $state | ConvertTo-Json | Set-Content -Path $StateFile
    } catch {
        Write-Error $_
    }
    """
    assert has_clean_restoration_logic("start_interview_mode.ps1", start_valid) is True

    start_invalid = "Stop-Service SysMain"
    assert has_clean_restoration_logic("start_interview_mode.ps1", start_invalid) is False

    # stop_interview_mode
    stop_valid = """
    try {
        $state = Get-Content -Path $StateFile | ConvertFrom-Json
        Start-Service -Name $state.Services
        Remove-Item -Path $StateFile -Force
    } catch {
        Write-Error $_
    }
    """
    assert has_clean_restoration_logic("stop_interview_mode.ps1", stop_valid) is True

    stop_invalid = "Start-Service SysMain"
    assert has_clean_restoration_logic("stop_interview_mode.ps1", stop_invalid) is False

    # optimize_windows_for_ai_dev
    opt_valid = """
    [CmdletBinding()]
    param([switch]$Restore)
    try {
        if ($Restore) { Restore-RegistryBackup }
    } catch {
        Write-Error $_
    }
    """
    assert has_clean_restoration_logic("optimize_windows_for_ai_dev.ps1", opt_valid) is True


# ==============================================================================
# TESTES DE CONTRATO DOS SCRIPTS ALVO (SHIFT-LEFT TDD)
# ==============================================================================


@pytest.mark.parametrize("script_name", TARGET_SCRIPTS)
def test_target_script_contract_and_guardrails(script_name: str) -> None:
    """
    Valida sintaxe AST e todos os guardrails obrigatórios nos scripts reais em scripts/.
    Caso o script ainda não exista, sinaliza pendência em conformidade com Shift-Left TDD.
    """
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        pytest.skip(f"Script {script_name} ainda pendente de implementação (Shift-Left TDD ativo)")

    # 1. Validação de Sintaxe AST PowerShell
    ok, errors = validate_powershell_ast(script_path)
    assert ok is True, f"Erros de sintaxe AST no script {script_name}: {errors}"

    content = script_path.read_text(encoding="utf-8")

    # 2. Guardrail: Verificação de Administrador
    assert has_admin_check(content) is True, (
        f"Script {script_name} deve possuir verificação obrigatória de privilégios de Administrador"
    )

    # 3. Guardrail: Suporte a -WhatIf / SupportsShouldProcess
    assert has_whatif_support(content) is True, (
        f"Script {script_name} deve suportar -WhatIf via SupportsShouldProcess"
    )

    # 4. Guardrail: Métricas de Memória Antes/Depois
    assert has_memory_metrics(content) is True, (
        f"Script {script_name} deve coletar e exibir métricas de memória antes/depois"
    )

    # 5. Guardrail: Reversibilidade e Restauração Limpa
    assert has_clean_restoration_logic(script_name, content) is True, (
        f"Script {script_name} deve implementar modo de restauração limpa e reversibilidade"
    )
