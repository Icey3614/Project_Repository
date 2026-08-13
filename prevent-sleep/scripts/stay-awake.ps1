# stay-awake.ps1 - Hold a Windows sleep-prevention request while Codex runs a task.
# Commands: start | stop | status
param(
    [string]$Command = 'status',
    [double]$MaxHours = 12,
    [int]$ParentPid = 0,
    [switch]$PreventDisplaySleep,
    [string]$Token = 'default'
)

$ErrorActionPreference = 'Stop'
$stateFile = Join-Path $env:TEMP ("codex-stay-awake-{0}.state" -f $Token)
# ES_CONTINUOUS(0x80000000) | ES_SYSTEM_REQUIRED(1) = 2147483649
$flags = 2147483649
if ($PreventDisplaySleep) { $flags += 2 }  # + ES_DISPLAY_REQUIRED(2)

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class ES {
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
'@

function Get-HolderPid {
    if (Test-Path -LiteralPath $stateFile) {
        $line = Get-Content -LiteralPath $stateFile | Where-Object { $_ -like 'pid=*' } | Select-Object -First 1
        if ($line) { return [int]($line -replace '^pid=', '') }
    }
    return 0
}

function Write-State {
    param([int]$HolderPid, [string]$RequestReturn, [string]$LastHeartbeat = '')
    $lines = @(
        "pid=$HolderPid",
        "token=$Token",
        "flags=$flags",
        "started=$((Get-Date).ToString('o'))",
        "maxSeconds=$([int]($MaxHours * 3600))",
        "parentPid=$ParentPid",
        "requestReturn=$RequestReturn"
    )
    if ($LastHeartbeat) { $lines += "lastHeartbeat=$LastHeartbeat" }
    Set-Content -LiteralPath $stateFile -Value $lines -Encoding ASCII
}

function Invoke-Hold {
    if ($ParentPid -eq 0) {
        $codex = Get-Process -Name 'codex' -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($codex) { $ParentPid = $codex.Id }
    }
    $started = Get-Date
    $deadline = $started.AddSeconds($MaxHours * 3600)
    $r = [ES]::SetThreadExecutionState([uint32]$flags)
    if ($r -eq 0) {
        Write-Output "ERROR: SetThreadExecutionState failed (returned 0); cannot hold sleep prevention."
        exit 1
    }
    Write-State -HolderPid $PID -RequestReturn $r
    try {
        while ($true) {
            if ($ParentPid -gt 0 -and -not (Get-Process -Id $ParentPid -ErrorAction SilentlyContinue)) { break }
            if ((Get-Date) -ge $deadline) { break }
            [void][ES]::SetThreadExecutionState([uint32]$flags)
            Write-State -HolderPid $PID -RequestReturn $r -LastHeartbeat (Get-Date).ToString('o')
            $remaining = ($deadline - (Get-Date)).TotalSeconds
            Start-Sleep -Seconds ([Math]::Min(60, [Math]::Max(1, [int]$remaining)))
        }
    } finally {
        # Release the request; ES_CONTINUOUS alone clears SYSTEM/DISPLAY flags.
        [void][ES]::SetThreadExecutionState([uint32]2147483648)
        Remove-Item -LiteralPath $stateFile -Force -ErrorAction SilentlyContinue
    }
}

switch ($Command.ToLowerInvariant()) {
    'start' {
        $existing = Get-HolderPid
        if ($existing -gt 0 -and (Get-Process -Id $existing -ErrorAction SilentlyContinue)) {
            Write-Output "ALREADY_ACTIVE pid=$existing state=$stateFile"
            exit 0
        }
        Remove-Item -LiteralPath $stateFile -Force -ErrorAction SilentlyContinue
        $childArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $PSCommandPath, '-Command', 'hold', '-Token', $Token, '-MaxHours', $MaxHours)
        if ($PreventDisplaySleep) { $childArgs += '-PreventDisplaySleep' }
        $child = Start-Process -FilePath 'powershell.exe' -ArgumentList $childArgs -WindowStyle Hidden -PassThru
        Start-Sleep -Seconds 2
        if ($child.HasExited) {
            Write-Output "ERROR: holder exited early (code $($child.ExitCode)); start failed."
            exit 1
        }
        Write-Output "STARTED pid=$($child.Id) state=$stateFile"
        exit 0
    }
    'stop' {
        $holder = Get-HolderPid
        if ($holder -gt 0 -and (Get-Process -Id $holder -ErrorAction SilentlyContinue)) {
            Stop-Process -Id $holder -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
        }
        Remove-Item -LiteralPath $stateFile -Force -ErrorAction SilentlyContinue
        Write-Output 'STOPPED'
        exit 0
    }
    'status' {
        $holder = Get-HolderPid
        if ($holder -gt 0 -and (Get-Process -Id $holder -ErrorAction SilentlyContinue)) {
            Write-Output 'ACTIVE'
            Get-Content -LiteralPath $stateFile | ForEach-Object { Write-Output $_ }
            exit 0
        }
        if (Test-Path -LiteralPath $stateFile) {
            Remove-Item -LiteralPath $stateFile -Force -ErrorAction SilentlyContinue
            Write-Output 'INACTIVE (stale state cleaned)'
        } else {
            Write-Output 'INACTIVE'
        }
        exit 0
    }
    'hold' { Invoke-Hold }
    default {
        Write-Output "ERROR: unknown command '$Command' (use start|stop|status)"
        exit 1
    }
}
