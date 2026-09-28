#Requires -Version 7.0
#Requires -RunAsAdministrator

[CmdletBinding()]
param(
    [string]$ClientRoot = "",
    [ValidateRange(1, 65535)]
    [int]$ServerPort = 19150,
    [switch]$TemporarilyEnableFirewallProfiles
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($ClientRoot)) {
    $ClientRoot = Join-Path $repoRoot "build\army3-local-client"
}
$clientRootPath = (Resolve-Path -LiteralPath $ClientRoot).Path
$buildRootPath = (Resolve-Path -LiteralPath (Join-Path $repoRoot "build")).Path
$relativeToBuild = [System.IO.Path]::GetRelativePath($buildRootPath, $clientRootPath)
if ($relativeToBuild -eq ".." -or $relativeToBuild.StartsWith("..\")) {
    throw "ClientRoot must remain under $buildRootPath"
}

$clientExe = Join-Path $clientRootPath "Mobi Army 3 HA.exe"
$marker = Join-Path $clientRootPath ".army3-local-copy.json"
if (-not (Test-Path -LiteralPath $clientExe -PathType Leaf)) {
    throw "Patched client executable is missing: $clientExe"
}
if (-not (Test-Path -LiteralPath $marker -PathType Leaf)) {
    throw "Patched-copy marker is missing: $marker"
}

$python = (Get-Command python -ErrorAction Stop).Source
Push-Location $repoRoot
try {
    & $python -m tools.redirect_client verify-copy --output $clientRootPath
    if ($LASTEXITCODE -ne 0) {
        throw "Patched client verification failed"
    }
}
finally {
    Pop-Location
}

$disabledProfiles = @(Get-NetFirewallProfile | Where-Object { -not $_.Enabled })
$profilesToRestore = @($disabledProfiles | Select-Object -ExpandProperty Name)
$ruleGroup = "Army3LocalIsolation-$PID-$([Guid]::NewGuid().ToString('N'))"
$clientExitCode = 0
$blockedIPv4 = @(
    "0.0.0.0-126.255.255.255",
    "128.0.0.0-255.255.255.255"
)
$blockedIPv6 = @(
    "::-::",
    "::2-ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"
)

try {
    if ($disabledProfiles.Count -ne 0) {
        $names = $profilesToRestore -join ", "
        if (-not $TemporarilyEnableFirewallProfiles) {
            throw "All Windows Firewall profiles must be enabled; disabled: $names. Re-run with -TemporarilyEnableFirewallProfiles only after explicit approval."
        }
        Set-NetFirewallProfile -Profile $profilesToRestore -Enabled True
        $stillDisabled = @(
            Get-NetFirewallProfile -Name $profilesToRestore |
                Where-Object { -not $_.Enabled }
        )
        if ($stillDisabled.Count -ne 0) {
            throw "Failed to enable every required Windows Firewall profile"
        }
        Write-Warning "Temporarily enabled Windows Firewall profiles: $names"
    }

    if (-not (Test-NetConnection -ComputerName "127.0.0.1" -Port $ServerPort -InformationLevel Quiet)) {
        throw "Local server is not listening on 127.0.0.1:$ServerPort"
    }

    $executables = @(Get-ChildItem -LiteralPath $clientRootPath -Recurse -File -Filter "*.exe")
    if ($executables.Count -eq 0) {
        throw "No executable files found in patched client copy"
    }

    $index = 0
    foreach ($executable in $executables) {
        $index++
        New-NetFirewallRule `
            -DisplayName "$ruleGroup-v4-$index" `
            -Group $ruleGroup `
            -Direction Outbound `
            -Action Block `
            -Enabled True `
            -Profile Any `
            -Program $executable.FullName `
            -Protocol Any `
            -RemoteAddress $blockedIPv4 | Out-Null
        New-NetFirewallRule `
            -DisplayName "$ruleGroup-v6-$index" `
            -Group $ruleGroup `
            -Direction Outbound `
            -Action Block `
            -Enabled True `
            -Profile Any `
            -Program $executable.FullName `
            -Protocol Any `
            -RemoteAddress $blockedIPv6 | Out-Null
    }

    Write-Host "Isolation active for $($executables.Count) executable(s)."
    Write-Host "Only loopback traffic is outside the firewall block ranges."
    # Ask the existing desktop shell to launch the client at the interactive
    # user's normal integrity level.  The launcher remains elevated only to
    # own the temporary firewall rules.
    $knownClientIds = @(
        Get-CimInstance Win32_Process |
            Where-Object { $_.ExecutablePath -eq $clientExe } |
            Select-Object -ExpandProperty ProcessId
    )
    $quotedClientExe = '"' + $clientExe + '"'
    Start-Process `
        -FilePath (Join-Path $env:WINDIR "explorer.exe") `
        -ArgumentList $quotedClientExe | Out-Null

    $launchDeadline = [DateTime]::UtcNow.AddSeconds(15)
    $clientProcess = $null
    while ($null -eq $clientProcess -and [DateTime]::UtcNow -lt $launchDeadline) {
        Start-Sleep -Milliseconds 200
        $candidate = Get-CimInstance Win32_Process |
            Where-Object {
                $_.ExecutablePath -eq $clientExe -and
                $_.ProcessId -notin $knownClientIds
            } |
            Select-Object -First 1
        if ($null -ne $candidate) {
            $clientProcess = Get-Process -Id $candidate.ProcessId
        }
    }
    if ($null -eq $clientProcess) {
        throw "Client did not start through the interactive desktop shell"
    }

    $observedAuxLoopback = [System.Collections.Generic.HashSet[string]]::new()
    while (-not $clientProcess.HasExited) {
        $connections = @(
            Get-NetTCPConnection -OwningProcess $clientProcess.Id -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.State -in @(
                        "Established",
                        "SynSent",
                        "SynReceived",
                        "CloseWait",
                        "FinWait1",
                        "FinWait2"
                    )
                }
        )
        $unexpected = @(
            $connections | Where-Object {
                $_.RemoteAddress -notin @("127.0.0.1", "::1")
            }
        )
        if ($unexpected.Count -ne 0) {
            Stop-Process -Id $clientProcess.Id -Force
            $destinations = ($unexpected | ForEach-Object {
                "$($_.RemoteAddress):$($_.RemotePort)"
            }) -join ", "
            throw "Unexpected client TCP destination observed: $destinations"
        }
        foreach ($connection in $connections) {
            if (
                $connection.RemoteAddress -in @("127.0.0.1", "::1") -and
                $connection.RemotePort -ne $ServerPort
            ) {
                $destination = "$($connection.RemoteAddress):$($connection.RemotePort)"
                if ($observedAuxLoopback.Add($destination)) {
                    Write-Warning "Auxiliary loopback destination observed: $destination"
                }
            }
        }
        Start-Sleep -Milliseconds 200
        $clientProcess.Refresh()
    }

    $clientExitCode = $clientProcess.ExitCode
}
finally {
    Get-NetFirewallRule -Group $ruleGroup -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule -ErrorAction SilentlyContinue
    Write-Host "Isolation firewall rules removed."
    if ($profilesToRestore.Count -ne 0 -and $TemporarilyEnableFirewallProfiles) {
        try {
            Set-NetFirewallProfile -Profile $profilesToRestore -Enabled False
            $names = $profilesToRestore -join ", "
            Write-Host "Restored initially disabled Windows Firewall profiles: $names"
        }
        catch {
            Write-Error "Could not restore the original disabled firewall profiles: $_"
        }
    }
}

exit $clientExitCode
