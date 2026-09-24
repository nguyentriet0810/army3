[CmdletBinding()]
param(
    [string]$SourceDirectory = (Join-Path $PSScriptRoot '..\analysis\generated\cpp2il\diffable-cs\DiffableCs'),
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '..\analysis\generated\cpp2il\index')
)

$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath $SourceDirectory -ErrorAction Stop).Path.TrimEnd('\', '/')
$output = [System.IO.Path]::GetFullPath($OutputDirectory)

if ($output.Equals($source, [System.StringComparison]::OrdinalIgnoreCase) -or
    $output.StartsWith($source + [System.IO.Path]::DirectorySeparatorChar,
        [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'OutputDirectory must not be inside SourceDirectory.'
}

if ((Test-Path -LiteralPath $output) -and
    (Get-ChildItem -LiteralPath $output -Force | Select-Object -First 1)) {
    throw "OutputDirectory is not empty: $output"
}

New-Item -ItemType Directory -Path $output -Force | Out-Null
$encoding = [System.Text.UTF8Encoding]::new($false)
$assemblies = [System.IO.StreamWriter]::new((Join-Path $output 'assemblies.txt'), $false, $encoding)
$types = [System.IO.StreamWriter]::new((Join-Path $output 'type-files.txt'), $false, $encoding)
$methods = [System.IO.StreamWriter]::new((Join-Path $output 'method-signatures.txt'), $false, $encoding)
$fields = [System.IO.StreamWriter]::new((Join-Path $output 'field-signatures.txt'), $false, $encoding)

$methodCount = 0
$fieldCount = 0
$typeFileCount = 0
$methodPattern = '^\s*(?:(?:public|private|protected|internal|static|sealed|virtual|override|abstract|extern|unsafe|new|async|partial)\s+)+[^\r\n]*\([^;\r\n]*\)\s*\{\s*\}\s*$'

try {
    foreach ($assembly in (Get-ChildItem -LiteralPath $source -Directory | Sort-Object Name)) {
        $assemblies.WriteLine($assembly.Name)
    }

    foreach ($file in (Get-ChildItem -LiteralPath $source -Recurse -File -Filter '*.cs' | Sort-Object FullName)) {
        $relative = $file.FullName.Substring($source.Length + 1)
        $types.WriteLine($relative)
        $typeFileCount++
        $lineNumber = 0
        foreach ($line in [System.IO.File]::ReadLines($file.FullName)) {
            $lineNumber++
            if ($line -match $methodPattern) {
                $methods.WriteLine("${relative}:${lineNumber}`t$($line.Trim())")
                $methodCount++
            }
            if ($line.Contains('//Field offset:')) {
                $fields.WriteLine("${relative}:${lineNumber}`t$($line.Trim())")
                $fieldCount++
            }
        }
    }
}
finally {
    $assemblies.Dispose()
    $types.Dispose()
    $methods.Dispose()
    $fields.Dispose()
}

Write-Output "Type source files: $typeFileCount"
Write-Output "Method signatures (heuristic): $methodCount"
Write-Output "Field signatures (heuristic): $fieldCount"
Write-Output "Index: $output"
