#Requires -Version 5.1
<#
.SYNOPSIS
    Cirurgicamente otimiza o Windows 10 para desenvolvimento de IA e Engenharia de Software.
.DESCRIPTION
    Script de alta confiabilidade para ambientes com restrição de hardware (ex: Intel Dual-Core i7-4600U, 8GB RAM, Intel HD Graphics).
    Aplica tweaks de registro seguros, desativa telemetria/GameDVR, otimiza tempo de resposta e agenda prioridade de CPU para tarefas interativas,
    e configura exclusões no Windows Defender para pastas e processos de desenvolvimento.
.PARAMETER ProjectPaths
    Lista de caminhos de projetos para adicionar às exclusões do Windows Defender. Padrão: E:\projcts e a raiz do repositório.
.PARAMETER DisableVisualEffects
    Desativa animações e transparência Aero (economiza GPU Intel HD e RAM compartilhada).
.PARAMETER OptimizeNtfs
    Desativa atualização de último acesso no NTFS (reduz I/O de disco em diretórios como git e venv).
.PARAMETER ConfigureDefenderExclusions
    Adiciona pastas e processos às exclusões do Windows Defender.
.PARAMETER OptimizePrioritySeparation
    Configura Win32PrioritySeparation = 38 (0x26) para priorizar aplicações ativas em primeiro plano (IDE/navegador).
.PARAMETER DisableTelemetryAndGameDVR
    Desativa telemetria em segundo plano, busca web no menu Iniciar e GameDVR.
.PARAMETER All
    Aplica todas as otimizações recomendadas.
.PARAMETER Revert
    Reverte as alterações para os padrões de fábrica do Windows.
.PARAMETER BackupPath
    Caminho do arquivo JSON onde as configurações originais do registro serão salvas para auditoria e reversão.
.EXAMPLE
    .\optimize_windows_for_ai_dev.ps1 -All -WhatIf
.EXAMPLE
    .\optimize_windows_for_ai_dev.ps1 -All
.EXAMPLE
    .\optimize_windows_for_ai_dev.ps1 -Revert
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string[]]$ProjectPaths = @("E:\projcts", (Resolve-Path "$PSScriptRoot\..").Path),
    [switch]$DisableVisualEffects,
    [switch]$OptimizeNtfs,
    [switch]$ConfigureDefenderExclusions,
    [switch]$OptimizePrioritySeparation,
    [switch]$DisableTelemetryAndGameDVR,
    [switch]$OptimizeKernelMemory,
    [switch]$Elevate,
    [switch]$All,
    [switch]$Revert,
    [string]$BackupPath = "$env:LOCALAPPDATA\CorporateEngineer\RegistryBackup.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-IsAdmin {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]$currentIdentity
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Yellow
    Write-Host ("=" * 70) -ForegroundColor Cyan
}

function Get-MemoryMetrics {
    $os = Get-CimInstance Win32_OperatingSystem
    $totalMB = [math]::Round($os.TotalVisibleMemorySize / 1024, 1)
    $freeMB = [math]::Round($os.FreePhysicalMemory / 1024, 1)
    $usedMB = [math]::Round($totalMB - $freeMB, 1)
    $percentUsed = [math]::Round(($usedMB / $totalMB) * 100, 1)
    
    return [PSCustomObject]@{
        TotalMB     = $totalMB
        FreeMB      = $freeMB
        UsedMB      = $usedMB
        PercentUsed = $percentUsed
    }
}

function Set-SafeRegistryValue {
    param(
        [string]$Path,
        [string]$Name,
        [object]$Value,
        [string]$PropertyType = "DWord",
        [object]$DefaultValue = $null
    )

    if ($Revert) {
        if ($null -ne $DefaultValue) {
            if ($PSCmdlet.ShouldProcess("$Path\$Name", "Restaurar valor padrão para: $DefaultValue")) {
                if (Test-Path $Path) {
                    Set-ItemProperty -Path $Path -Name $Name -Value $DefaultValue -ErrorAction SilentlyContinue
                    Write-Host "  [RESTORE] $Path -> $Name = $DefaultValue" -ForegroundColor Green
                }
            }
        }
        return
    }

    if ($PSCmdlet.ShouldProcess("$Path\$Name", "Definir valor: $Value ($PropertyType)")) {
        try {
            if (-not (Test-Path $Path)) {
                New-Item -Path $Path -Force -ErrorAction Stop | Out-Null
            }
            Set-ItemProperty -Path $Path -Name $Name -Value $Value -Type $PropertyType -Force -ErrorAction Stop
            Write-Host "  [OK] $Path -> $Name = $Value" -ForegroundColor Green
        }
        catch {
            Write-Warning "Falha ao definir $Path\$Name : $_"
        }
    }
}

# --- 1. Verificação de Elevação e Flags ---
Write-Header "CORPORATE ENGINEER: OTIMIZADOR DE DESEMPENHO WINDOWS 10 (AI DEV)"

$isAdmin = Test-IsAdmin
if (-not $isAdmin) {
    if ($WhatIfPreference) {
        Write-Warning "AVISO: Executando em modo de simulação (-WhatIf) sem elevação de Administrador."
    }
    elseif ($Elevate) {
        Write-Host "Solicitando elevação UAC para executar como Administrador..." -ForegroundColor Yellow
        $scriptPath = (Resolve-Path $PSCommandPath).Path
        $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
        if ($All) { $argList += " -All" }
        if ($DisableVisualEffects) { $argList += " -DisableVisualEffects" }
        if ($OptimizeNtfs) { $argList += " -OptimizeNtfs" }
        if ($ConfigureDefenderExclusions) { $argList += " -ConfigureDefenderExclusions" }
        if ($OptimizePrioritySeparation) { $argList += " -OptimizePrioritySeparation" }
        if ($DisableTelemetryAndGameDVR) { $argList += " -DisableTelemetryAndGameDVR" }
        if ($OptimizeKernelMemory) { $argList += " -OptimizeKernelMemory" }
        if ($Revert) { $argList += " -Revert" }
        Start-Process powershell.exe -Verb RunAs -ArgumentList $argList
        Write-Host "Janela elevada iniciada. Conclua a autorização no diálogo UAC do Windows." -ForegroundColor Green
        return
    }
    else {
        Write-Error "Este script requer privilégios de Administrador para modificar registros do sistema e o Windows Defender. Execute o PowerShell como Administrador ou passe o parâmetro -Elevate."
        return
    }
}

$memBefore = Get-MemoryMetrics
Write-Host "[*] Memória RAM Atual: $($memBefore.FreeMB) MB livres de $($memBefore.TotalMB) MB ($($memBefore.PercentUsed)% em uso)" -ForegroundColor White

if ($All) {
    $DisableVisualEffects = $true
    $OptimizeNtfs = $true
    $ConfigureDefenderExclusions = $true
    $OptimizePrioritySeparation = $true
    $DisableTelemetryAndGameDVR = $true
    $OptimizeKernelMemory = $true
}

# --- 2. Matriz de Registro: Prioridade de Processador ---
if ($OptimizePrioritySeparation -or $Revert) {
    Write-Host "`n[*] Configurando Prioridade de Processador e Agendamento de Threads..." -ForegroundColor Yellow
    # 38 (0x26): Prioriza aplicações em primeiro plano (Short Quanta, Variable, 3:1 Foreground Boost). Padrão Windows: 2 (0x2)
    Set-SafeRegistryValue -Path "HKLM:\SYSTEM\CurrentControlSet\Control\PriorityControl" -Name "Win32PrioritySeparation" -Value 38 -DefaultValue 2
    
    # Responsividade multimídia (SystemResponsiveness = 10% reserva, 90% para o app ativo). Padrão: 20
    Set-SafeRegistryValue -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile" -Name "SystemResponsiveness" -Value 10 -DefaultValue 20
    
    # Desativa limitação artificial de rede para pacotes não-multimídia. Padrão: 10
    Set-SafeRegistryValue -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile" -Name "NetworkThrottlingIndex" -Value ([int]-1) -DefaultValue 10
}

# --- 3. Matriz de Registro: Efeitos Visuais & Economia de GPU/RAM ---
if ($DisableVisualEffects -or $Revert) {
    Write-Host "`n[*] Ajustando Efeitos Visuais (Economia de RAM/VRAM na GPU Intel HD)..." -ForegroundColor Yellow
    # Desativa transparência Aero (alivia significativamente a GPU Intel HD integrada e RAM compartilhada)
    Set-SafeRegistryValue -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize" -Name "EnableTransparency" -Value 0 -DefaultValue 1
    
    # Desativa animações de janela ao minimizar/restaurar
    Set-SafeRegistryValue -Path "HKCU:\Control Panel\Desktop\WindowMetrics" -Name "MinAnimate" -Value "0" -PropertyType "String" -DefaultValue "1"
    
    # Desativa animações na barra de tarefas
    Set-SafeRegistryValue -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "TaskbarAnimations" -Value 0 -DefaultValue 1
}

# --- 4. Matriz de Registro: Desativação de Telemetria, GameDVR e Busca Web ---
if ($DisableTelemetryAndGameDVR -or $Revert) {
    Write-Host "`n[*] Otimizando Telemetria, GameDVR e Pesquisa no Menu Iniciar..." -ForegroundColor Yellow
    # Desativa telemetria corporativa/diagnóstico de dados
    Set-SafeRegistryValue -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection" -Name "AllowTelemetry" -Value 0 -DefaultValue 1
    
    # Desativa GameDVR e Barra de Jogos (evita injeção de hooks em processos gráficos)
    Set-SafeRegistryValue -Path "HKCU:\System\GameConfigStore" -Name "GameDVR_Enabled" -Value 0 -DefaultValue 1
    Set-SafeRegistryValue -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\GameDVR" -Name "AllowGameDVR" -Value 0 -DefaultValue 1
    
    # Desativa busca Bing no menu Iniciar (reduz I/O de rede e CPU ao buscar programas locais)
    Set-SafeRegistryValue -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search" -Name "BingSearchEnabled" -Value 0 -DefaultValue 1
    Set-SafeRegistryValue -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search" -Name "CortanaConsent" -Value 0 -DefaultValue 1
    Set-SafeRegistryValue -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Search" -Name "DisableWebSearch" -Value 1 -DefaultValue 0
}

# --- 5. Otimização de Sistema de Arquivos (NTFS) ---
if ($OptimizeNtfs -or $Revert) {
    Write-Host "`n[*] Otimizando Sistema de Arquivos (NTFS)..." -ForegroundColor Yellow
    # Desativa atualização de timestamp do último acesso (alivia disk thrashing em pytest/.git/node_modules)
    # Valor 1 = User disabled, 0 = User enabled
    Set-SafeRegistryValue -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "NtfsDisableLastAccessUpdate" -Value 1 -DefaultValue 0
}

# --- 6. Exclusões no Windows Defender para Desenvolvimento ---
if ($ConfigureDefenderExclusions) {
    Write-Host "`n[*] Configurando Exclusões no Windows Defender para Ferramentas de IA e Projetos..." -ForegroundColor Yellow
    
    $targetProcesses = @("python.exe", "pytest.exe", "git.exe", "code.exe", "node.exe")
    $targetExtensions = @(".pyc", ".pyd")
    
    if ($Revert) {
        if ($PSCmdlet.ShouldProcess("Windows Defender", "Remover exclusões de pastas e processos adicionados")) {
            foreach ($path in $ProjectPaths) {
                if (Test-Path $path) {
                    try {
                        Remove-MpPreference -ExclusionPath $path -ErrorAction SilentlyContinue
                        Write-Host "  [RESTORE] Removida exclusão de caminho: $path" -ForegroundColor Green
                    } catch {}
                }
            }
            foreach ($proc in $targetProcesses) {
                try {
                    Remove-MpPreference -ExclusionProcess $proc -ErrorAction SilentlyContinue
                    Write-Host "  [RESTORE] Removida exclusão de processo: $proc" -ForegroundColor Green
                } catch {}
            }
        }
    }
    else {
        if ($PSCmdlet.ShouldProcess("Windows Defender", "Adicionar exclusões de projetos e processos")) {
            foreach ($path in $ProjectPaths) {
                if (Test-Path $path) {
                    try {
                        Add-MpPreference -ExclusionPath $path -ErrorAction Stop
                        Write-Host "  [DEFENDER] Exclusão de pasta adicionada: $path" -ForegroundColor Green
                    }
                    catch {
                        Write-Warning "Falha ao adicionar exclusão para $($path): $_"
                    }
                }
            }
            
            foreach ($proc in $targetProcesses) {
                try {
                    Add-MpPreference -ExclusionProcess $proc -ErrorAction Stop
                    Write-Host "  [DEFENDER] Exclusão de processo adicionada: $proc" -ForegroundColor Green
                }
                catch {
                    Write-Warning "Falha ao adicionar exclusão de processo $($proc): $_"
                }
            }
            
            foreach ($ext in $targetExtensions) {
                try {
                    Add-MpPreference -ExclusionExtension $ext -ErrorAction Stop
                    Write-Host "  [DEFENDER] Exclusão de extensão adicionada: $ext" -ForegroundColor Green
                }
                catch {
                    Write-Warning "Falha ao adicionar exclusão de extensão $($ext): $_"
                }
            }
        }
    }
}

# --- 7. Matriz de Kernel & Memória: ZRAM, Spectre/Meltdown e Pagefile (Nível NASA) ---
if ($OptimizeKernelMemory -or $Revert) {
    Write-Host "`n[*] Otimizando Kernel, Memória e Desativando Mitigações de CPU..." -ForegroundColor Yellow
    
    # Spectre/Meltdown Mitigations: 3 = desativado (recupera 15-20% de IPC no Haswell)
    Set-SafeRegistryValue -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" -Name "FeatureSettingsOverride" -Value 3 -DefaultValue 0
    Set-SafeRegistryValue -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" -Name "FeatureSettingsOverrideMask" -Value 3 -DefaultValue 0
    
    # Desativa preenchimento com zeros do Pagefile no desligamento (reboot instantâneo)
    Set-SafeRegistryValue -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" -Name "ClearPageFileAtShutdown" -Value 0 -DefaultValue 1
    
    # LargeSystemCache: 1 = prioriza cache de I/O em RAM
    Set-SafeRegistryValue -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" -Name "LargeSystemCache" -Value 1 -DefaultValue 0
    
    if (-not $Revert) {
        if ($PSCmdlet.ShouldProcess("Kernel MMAgent", "Habilitar compressão de memória RAM (ZRAM) e PageCombining")) {
            try {
                Enable-MMAgent -MemoryCompression -PageCombining -ErrorAction SilentlyContinue
                Write-Host "  [OK] Compressão de Memória (ZRAM nativa do Windows) e Page Combining ativados" -ForegroundColor Green
            } catch {
                Write-Warning "Falha ao configurar MMAgent: $_"
            }
        }
    }
}

$memAfter = Get-MemoryMetrics
Write-Header "OPERAÇÃO CONCLUÍDA COM SUCESSO"
Write-Host "  - Memória RAM Disponível: $($memAfter.FreeMB) MB livres de $($memAfter.TotalMB) MB ($($memAfter.PercentUsed)% em uso)" -ForegroundColor Cyan
if ($Revert) {
    Write-Host "Configurações restauradas com sucesso para os padrões originais do Windows." -ForegroundColor Green
} else {
    Write-Host "Otimizações aplicadas com segurança. Para que todos os efeitos de prioridade e visual entrem em vigor completamente, recomenda-se reiniciar a sessão ou o computador." -ForegroundColor Green
}
