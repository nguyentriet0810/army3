param(
    [string]$ClientPath = (Join-Path $PSScriptRoot '..\Mobiarmy3HA_3.0.0_GOC')
)

$ErrorActionPreference = 'Stop'
$clientRoot = (Resolve-Path -LiteralPath $ClientPath).ProviderPath.TrimEnd('\', '/')
$files = @(Get-ChildItem -LiteralPath $clientRoot -Recurse -Force -File | Sort-Object FullName)
$totalBytes = ($files | Measure-Object -Property Length -Sum).Sum

Write-Output "Client root: $clientRoot"
Write-Output "Files: $($files.Count)"
Write-Output "Total bytes: $totalBytes"
Write-Output ''
Write-Output 'SHA-256 manifest (hash *relative/path):'

foreach ($file in $files) {
    $relativePath = $file.FullName.Substring($clientRoot.Length + 1).Replace('\', '/')
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
    Write-Output "$hash *$relativePath"
}
