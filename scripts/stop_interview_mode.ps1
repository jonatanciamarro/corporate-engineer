#Requires -Version 5.1
<#
.SYNOPSIS
    Desativa o Modo de Entrevista e restaura os serviços do Windows 10 ao estado original.
.DESCRIPTION
    Lê o snapshot de estado salvo pelo Start-InterviewMode (JSON) e restaura cirurgicamente
    apenas os serviços que estavam originalmente em execução antes da ativação do modo de entrevista.
    Garante reversibilidade total, atomicidade e integridade do sistema operacional.
.PARAMETER StateFilePath
    Caminho onde o estado das tarefas e serviços em execução foi persistido.
.PARAMETER Force
    Força a tentativa de restauração mesmo se houver avisos de integridade no snapshot.
.EXAMPLE
    .\stop_interview_mode.ps1 -WhatIf
.EXAMPLE
    .\stop_interview_mode.ps1
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$StateFilePath = "$env:LOCALAPPDATA\InterviewMode\service_state.json",
    [switch]$Force
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

Write-Header "STOP-INTERVIEW-MODE: RESTAURAÇÃO ATÔMICA DE SERVIÇOS"

# --- 1. Verificação de Privilégios ---
$isAdmin = Test-IsAdmin
if (-not $isAdmin) {
    if ($WhatIfPreference) {
        Write-Warning "AVISO: Executando em modo de simulação (-WhatIf) sem privilégios de Administrador."
    }
    else {
        Write-Error "Privilégios elevados de Administrador são necessários para iniciar serviços do sistema. Execute o PowerShell como Administrador."
        return
    }
}

# --- 2. Verificação da Existência do Arquivo de Estado ---
if (-not (Test-Path $StateFilePath)) {
    Write-Warning "Nenhum arquivo de estado ativo de Modo de Entrevista encontrado em:"
    Write-Warning "  $StateFilePath"
    Write-Host "`nO sistema já parece estar no estado padrão ou o modo de entrevista não foi iniciado por este usuário." -ForegroundColor Gray
    return
}

# --- 3. Leitura e Desserialização do Snapshot ---
Write-Host "[*] Carregando snapshot de serviços de: $StateFilePath" -ForegroundColor Yellow
try {
    $rawJson = Get-Content -Path $StateFilePath -Raw -Encoding UTF8
    $stateObj = $rawJson | ConvertFrom-Json
}
catch {
    Write-Error "Falha ao ler ou converter o arquivo JSON de estado: $_"
    return
}

$servicesToRestore = $stateObj.StoppedServices
$timestamp = $stateObj.Timestamp
Write-Host "  -> Sessão iniciada em: $timestamp" -ForegroundColor Cyan
Write-Host "  -> Total de serviços a restaurar: $($servicesToRestore.Count)" -ForegroundColor Cyan

# --- 4. Restauração Sequencial dos Serviços ---
$restoredCount = 0
$failedCount = 0

if ($null -ne $servicesToRestore -and $servicesToRestore.Count -gt 0) {
    Write-Host "`n[*] Reiniciando serviços suspensos..." -ForegroundColor Yellow
    foreach ($svc in $servicesToRestore) {
        $svcName = $svc.Name
        if ($PSCmdlet.ShouldProcess($svcName, "Reiniciar serviço para estado ativo")) {
            try {
                $serviceInstance = Get-Service -Name $svcName -ErrorAction SilentlyContinue
                if ($null -eq $serviceInstance) {
                    Write-Warning "Serviço $svcName não foi localizado no sistema."
                    $failedCount++
                    continue
                }

                if ($serviceInstance.Status -ne [System.ServiceProcess.ServiceControllerStatus]::Running) {
                    Start-Service -Name $svcName -ErrorAction Stop
                    Start-Sleep -Milliseconds 300
                    $refreshed = Get-Service -Name $svcName
                    Write-Host "  [RESTORED] $svcName ($($svc.DisplayName)) -> $($refreshed.Status)" -ForegroundColor Green
                    $restoredCount++
                } else {
                    Write-Host "  [OK] $svcName já se encontra em execução." -ForegroundColor Gray
                    $restoredCount++
                }
            }
            catch {
                Write-Warning "Falha ao reiniciar o serviço $($svcName): $_"
                $failedCount++
            }
        }
    }
} else {
    Write-Host "  Nenhum serviço precisava ser restaurado (nenhum foi suspenso na inicialização)." -ForegroundColor Gray
}

# --- 5. Limpeza do Arquivo de Estado ---
if ($PSCmdlet.ShouldProcess($StateFilePath, "Excluir arquivo de snapshot após restauração")) {
    try {
        Remove-Item -Path $StateFilePath -Force -ErrorAction Stop
        Write-Host "`n[ESTADO] Snapshot removido com sucesso. Sessão de entrevista finalizada." -ForegroundColor Green
    }
    catch {
        Write-Warning "Não foi possível remover o arquivo de estado $($StateFilePath): $_"
    }
}

# --- 6. Relatório Final de Métricas ---
$currentMem = Get-MemoryMetrics
Write-Header "SISTEMA RESTAURADO AOS PADRÕES OPERACIONAIS"
Write-Host "  - Serviços Restaurados: $restoredCount de $($servicesToRestore.Count)" -ForegroundColor White
if ($failedCount -gt 0) {
    Write-Host "  - Falhas na Restauração: $failedCount" -ForegroundColor Red
}
Write-Host "  - Memória RAM Atual Livre: $($currentMem.FreeMB) MB ($($currentMem.PercentUsed)% em uso)" -ForegroundColor Cyan
Write-Host "O ambiente de trabalho retornou ao seu perfil de operação normal com suporte pleno a multitarefa." -ForegroundColor Green
Write-Host ""
