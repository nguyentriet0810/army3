[CmdletBinding()]
param(
    [string]$ClientDirectory = (Join-Path $PSScriptRoot '..\Mobiarmy3HA_3.0.0_GOC'),
    [string]$ToolPath = (Join-Path $PSScriptRoot '..\tmp\cpp2il\Cpp2IL.exe'),
    [ValidateSet('dll_empty', 'diffable-cs', 'dll_il_recovery', 'isil')]
    [string]$OutputAs = 'diffable-cs',
    [string]$OutputDirectory,
    [string]$ExeName = 'Mobi Army 3 HA'
)

$ErrorActionPreference = 'Stop'

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $PSScriptRoot "..\analysis\generated\cpp2il\$OutputAs"
}

$client = (Resolve-Path -LiteralPath $ClientDirectory -ErrorAction Stop).Path
$tool = (Resolve-Path -LiteralPath $ToolPath -ErrorAction Stop).Path
$output = [System.IO.Path]::GetFullPath($OutputDirectory)
$clientPrefix = $client.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar

if ($output.Equals($client, [System.StringComparison]::OrdinalIgnoreCase) -or
    $output.StartsWith($clientPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'OutputDirectory must not be inside the original client directory.'
}

$gameAssembly = Join-Path $client 'GameAssembly.dll'
$metadata = Join-Path $client 'Mobi Army 3 HA_Data\il2cpp_data\Metadata\global-metadata.dat'
$gameExe = Join-Path $client "$ExeName.exe"

foreach ($inputPath in @($gameAssembly, $metadata, $gameExe)) {
    if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) {
        throw "Missing input: $inputPath"
    }
}

if ((Test-Path -LiteralPath $output) -and
    (Get-ChildItem -LiteralPath $output -Force | Select-Object -First 1)) {
    throw "OutputDirectory is not empty: $output"
}

New-Item -ItemType Directory -Path $output -Force | Out-Null

$toolArgs = @(
    "--game-path=$client"
    "--exe-name=$ExeName"
    "--output-as=$OutputAs"
    "--output-to=$output"
)

& $tool @toolArgs
if ($LASTEXITCODE -ne 0) {
    throw "Cpp2IL failed with exit code $LASTEXITCODE"
}

Write-Output "Cpp2IL output: $output"
