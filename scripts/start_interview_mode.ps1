#Requires -Version 5.1
<#
.SYNOPSIS
    Ativa o Modo de Entrevista e Live Coding de Alto Desempenho no Windows 10.
.DESCRIPTION
    Script cirúrgico para máquinas com hardware restrito (Intel Dual-Core, 8GB RAM).
    Pausa temporariamente serviços pesados não-essenciais de segundo plano (Windows Search, SysMain, Windows Update, Spooler, Telemetria),
    libera memória RAM (Working Set Trim), eleva a prioridade de processos da IDE e conferência, e salva o estado original em JSON para reversão atômica.
    Invariantes garantidas: Rede, áudio, webcam e subsistemas vitais NUNCA são tocados.
.PARAMETER StateFilePath
    Caminho onde o estado das tarefas e serviços em execução será salvo.
.PARAMETER TrimWorkingSets
    Executa a coleta de lixo e limpeza de Working Set de memória de processos ociosos em segundo plano.
.PARAMETER BoostDevPriorities
    Eleva a prioridade de processos de desenvolvimento e videoconferência (VS Code, Python, Chrome, Meet, Zoom, Teams) para 'AboveNormal'.
.PARAMETER CandidateServices
    Lista de serviços não-essenciais candidatos a suspensão durante o modo de entrevista.
.EXAMPLE
    .\start_interview_mode.ps1 -WhatIf
.EXAMPLE
    .\start_interview_mode.ps1 -TrimWorkingSets -BoostDevPriorities
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$StateFilePath = "$env:LOCALAPPDATA\InterviewMode\service_state.json",
    [switch]$TrimWorkingSets = $true,
    [switch]$BoostDevPriorities = $true,
    [string[]]$CandidateServices = @(
        'WSearch',          # Windows Search Indexer (eats 150-350MB RAM + CPU disk thrashing)
        'SysMain',          # SuperFetch / SysMain (eats background RAM and disk quanta)
        'DiagTrack',        # Telemetria e Diagnóstico de Usuário
        'dmwappushservice', # WAP Push Service de telemetria
        'Spooler',          # Spooler de Impressão (desnecessário em entrevistas)
        'wuauserv',         # Windows Update (previne downloads e atualizações surpresa)
        'BITS',             # Background Intelligent Transfer Service
        'XblAuthManager',   # Xbox Live Auth
        'XblGameSave',      # Xbox Live Game Save
        'XboxNetApiSvc',    # Xbox Live Networking
        'XboxGipSvc',       # Xbox Accessory Management
        'MapsBroker',       # Downloaded Maps Manager
        'RetailDemo',       # Retail Demo Service
        'WerSvc'            # Windows Error Reporting
    ),
    [string[]]$PriorityProcesses = @('code', 'python', 'chrome', 'msedge', 'zoom', 'teams', 'slack')
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

Write-Header "START-INTERVIEW-MODE: ALOCAÇÃO CIRÚRGICA DE PERFORMANCE"

# --- 1. Verificação de Privilégios ---
$isAdmin = Test-IsAdmin
if (-not $isAdmin) {
    if ($WhatIfPreference) {
        Write-Warning "AVISO: Executando em modo de simulação (-WhatIf) sem privilégios de Administrador."
    }
    else {
        Write-Error "Privilégios elevados de Administrador são necessários para pausar serviços do sistema. Execute o PowerShell como Administrador."
        return
    }
}

# --- 2. Invariante de Segurança: Blacklist Crítica ---
$criticalServicesBlacklist = @(
    'AudioSrv', 'AudioEndpointBuilder', 'Dhcp', 'Dnscache', 'LanmanWorkstation',
    'LanmanServer', 'WlanSvc', 'Netman', 'NlaSvc', 'nsi', 'BFE', 'MpsSvc',
    'WinHttpAutoProxySvc', 'FrameServer', 'EventLog', 'PlugPlay', 'RpcSs',
    'RpcEptMapper', 'DcomLaunch', 'SamSs', 'LSM', 'ProfSvc', 'CryptSvc'
)

foreach ($blacklisted in $criticalServicesBlacklist) {
    if ($CandidateServices -contains $blacklisted) {
        throw "VIOLAÇÃO DE INVARIANTE: O serviço crítico '$blacklisted' não pode ser pausado!"
    }
}

# --- 3. Coleta de Métricas Iniciais de Memória ---
$memBefore = Get-MemoryMetrics
Write-Host "[*] Memória RAM Inicial: $($memBefore.FreeMB) MB livres de $($memBefore.TotalMB) MB ($($memBefore.PercentUsed)% em uso)" -ForegroundColor White

# --- 4. Descoberta e Filtro de Serviços em Execução ---
Write-Host "`n[*] Identificando serviços não-essenciais em execução..." -ForegroundColor Yellow
$servicesToStop = @()

foreach ($svcName in $CandidateServices) {
    $svc = Get-Service -Name $svcName -ErrorAction SilentlyContinue
    if ($null -ne $svc -and $svc.Status -eq [System.ServiceProcess.ServiceControllerStatus]::Running) {
        $servicesToStop += [PSCustomObject]@{
            Name        = $svc.Name
            DisplayName = $svc.DisplayName
            Status      = "Running"
            StartType   = $svc.StartType.ToString()
        }
        Write-Host "  -> Encontrado ativo: $($svc.Name) ($($svc.DisplayName))" -ForegroundColor Cyan
    }
}

# --- 5. Persistência de Estado (Garantia de Reversibilidade Total) ---
$stateDir = Split-Path -Path $StateFilePath -Parent
if (-not (Test-Path $stateDir)) {
    New-Item -Path $stateDir -ItemType Directory -Force | Out-Null
}

$statePayload = [PSCustomObject]@{
    Timestamp          = (Get-Date).ToString("o")
    HostName           = $env:COMPUTERNAME
    InitialFreeMemoryMB= $memBefore.FreeMB
    StoppedServices    = $servicesToStop
    IsActive           = $true
}

if ($PSCmdlet.ShouldProcess($StateFilePath, "Salvar snapshot de estado dos serviços")) {
    $stateJson = $statePayload | ConvertTo-Json -Depth 4
    Set-Content -Path $StateFilePath -Value $stateJson -Encoding UTF8
    Write-Host "  [ESTADO] Snapshot salvo com sucesso em: $StateFilePath" -ForegroundColor Green
}

# --- 6. Pausa Segura dos Serviços ---
if ($servicesToStop.Count -gt 0) {
    Write-Host "`n[*] Pausando serviços não-essenciais com segurança..." -ForegroundColor Yellow
    foreach ($svc in $servicesToStop) {
        if ($PSCmdlet.ShouldProcess($svc.Name, "Parar serviço")) {
            try {
                Stop-Service -Name $svc.Name -Force -NoWait -ErrorAction Stop
                Write-Host "  [STOPPED] $($svc.Name) pausado." -ForegroundColor Green
            }
            catch {
                Write-Warning "Não foi possível pausar $($svc.Name): $_"
            }
        }
    }
} else {
    Write-Host "  Nenhum dos serviços candidatos estava em execução. Nenhuma parada necessária." -ForegroundColor Gray
}

# --- 7. Otimização de Working Set de Memória (RAM Purge) ---
if ($TrimWorkingSets) {
    Write-Host "`n[*] Executando purga e compactação de memória RAM (Working Set Trim)..." -ForegroundColor Yellow
    if ($PSCmdlet.ShouldProcess("Sistema", "Limpar Working Sets de processos ociosos")) {
        [System.GC]::Collect()
        [System.GC]::WaitForPendingFinalizers()

        $pInvokeDef = @"
using System;
using System.Runtime.InteropServices;
public class MemoryOptimizer {
    [DllImport("psapi.dll")]
    public static extern int EmptyWorkingSet(IntPtr hwProc);
}
"@
        try {
            if (-not ([System.Management.Automation.PSTypeName]'MemoryOptimizer').Type) {
                Add-Type -TypeDefinition $pInvokeDef -ErrorAction SilentlyContinue
            }
            $targetProcs = Get-Process | Where-Object {
                $_.Id -ne $PID -and
                $_.ProcessName -notmatch '^(idle|system|csrss|smss|services|lsass|svchost)$'
            }
            $trimmedCount = 0
            foreach ($p in $targetProcs) {
                try {
                    [MemoryOptimizer]::EmptyWorkingSet($p.Handle) | Out-Null
                    $trimmedCount++
                } catch {}
            }
            Write-Host "  [TRIM] $trimmedCount processos tiveram seus Working Sets otimizados." -ForegroundColor Green
        }
        catch {
            Write-Warning "Aviso na chamada P/Invoke de EmptyWorkingSet: $_"
        }
    }
}

# --- 8. Elevação de Prioridade para Ferramentas de IA e Entrevista ---
if ($BoostDevPriorities) {
    Write-Host "`n[*] Elevando prioridade de CPU para ferramentas de Desenvolvimento e Áudio/Vídeo..." -ForegroundColor Yellow
    foreach ($procName in $PriorityProcesses) {
        $procs = Get-Process -Name $procName -ErrorAction SilentlyContinue
        if ($null -ne $procs) {
            foreach ($p in $procs) {
                if ($PSCmdlet.ShouldProcess("$($p.ProcessName) (PID: $($p.Id))", "Definir prioridade para AboveNormal")) {
                    try {
                        $p.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::AboveNormal
                        Write-Host "  [PRIORITY] $($p.ProcessName) (PID: $($p.Id)) -> AboveNormal" -ForegroundColor Green
                    }
                    catch {
                        Write-Warning "Falha ao ajustar prioridade de $($p.ProcessName): $_"
                    }
                }
            }
        }
    }
}

# --- 9. Métricas Finais e Relatório ---
$memAfter = Get-MemoryMetrics
$freedMB = [math]::Round($memAfter.FreeMB - $memBefore.FreeMB, 1)

Write-Header "MODO DE ENTREVISTA ATIVADO COM SUCESSO"
Write-Host "  - Memória Livre Antes: $($memBefore.FreeMB) MB" -ForegroundColor White
Write-Host "  - Memória Livre Agora: $($memAfter.FreeMB) MB" -ForegroundColor Green
Write-Host "  - Saldo de RAM Liberado: $(if ($freedMB -gt 0) { "+$freedMB MB" } else { "$freedMB MB" })" -ForegroundColor Cyan
Write-Host "  - Serviços Suspensos: $($servicesToStop.Count)" -ForegroundColor White
Write-Host ""
Write-Host "IMPORTANTE: Para retornar ao estado normal ao término da entrevista, execute:" -ForegroundColor Yellow
Write-Host "  .\scripts\stop_interview_mode.ps1" -ForegroundColor Cyan
Write-Host ""
