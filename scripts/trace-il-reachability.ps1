[CmdletBinding()]
param(
    [string]$AssemblyPath = (Join-Path $PSScriptRoot '..\analysis\generated\cpp2il\dll_il_recovery\Assembly-CSharp.dll'),
    [Parameter(Mandatory = $true)][string]$CallsPath,
    [Parameter(Mandatory = $true)][string[]]$StartTokens,
    [Parameter(Mandatory = $true)][string]$TargetToken,
    [ValidateRange(1, 12)][int]$MaxDepth = 4
)

$ErrorActionPreference = 'Stop'
$assembly = (Resolve-Path -LiteralPath $AssemblyPath -ErrorAction Stop).Path
$calls = (Resolve-Path -LiteralPath $CallsPath -ErrorAction Stop).Path

function Convert-Token {
    param([string]$Value)
    if ($Value -notmatch '^0x[0-9a-fA-F]{8}$') {
        throw "Expected method token in 0x06000000 format: $Value"
    }
    return [Convert]::ToInt32($Value.Substring(2), 16)
}

$stream = [System.IO.File]::OpenRead($assembly)
try {
    $pe = [System.Reflection.PortableExecutable.PEReader]::new($stream)
    $reader = [System.Reflection.Metadata.PEReaderExtensions]::GetMetadataReader($pe)
    $nameByToken = @{}
    $tokensByName = @{}

    function Get-TypeName {
        param($Handle)
        $type = $reader.GetTypeDefinition($Handle)
        $name = $reader.GetString($type.Name)
        $parent = $type.GetDeclaringType()
        if (-not $parent.IsNil) {
            return (Get-TypeName $parent) + '+' + $name
        }
        $namespace = $reader.GetString($type.Namespace)
        if ($namespace) { return $namespace + '.' + $name }
        return $name
    }

    foreach ($typeHandle in $reader.TypeDefinitions) {
        $type = $reader.GetTypeDefinition($typeHandle)
        $typeName = Get-TypeName $typeHandle
        foreach ($methodHandle in $type.GetMethods()) {
            $token = [System.Reflection.Metadata.Ecma335.MetadataTokens]::GetToken([System.Reflection.Metadata.EntityHandle]$methodHandle)
            $name = $typeName + '::' + $reader.GetString($reader.GetMethodDefinition($methodHandle).Name)
            $nameByToken[$token] = $name
            if (-not $tokensByName.ContainsKey($name)) {
                $tokensByName[$name] = [System.Collections.Generic.List[int]]::new()
            }
            $tokensByName[$name].Add($token)
        }
    }

    $target = Convert-Token $TargetToken
    if (-not $nameByToken.ContainsKey($target)) { throw "Target method not found: $TargetToken" }
    $starts = @($StartTokens | ForEach-Object { Convert-Token $_ })
    foreach ($start in $starts) {
        if (-not $nameByToken.ContainsKey($start)) { throw ('Start method not found: 0x{0:X8}' -f $start) }
    }

    $edges = @{}
    $unresolved = @{}
    foreach ($row in (Import-Csv -LiteralPath $calls -Delimiter ([char]9))) {
        if ($row.opcode -notin @('call', 'callvirt', 'newobj', 'ldftn', 'ldvirtftn')) { continue }
        $caller = Convert-Token $row.method_token
        if (-not $edges.ContainsKey($caller)) {
            $edges[$caller] = [System.Collections.Generic.List[object]]::new()
        }
        if ($tokensByName.ContainsKey($row.target)) {
            # Overloads share a textual name in the dump. Keep all matches: this is an over-approximation.
            foreach ($callee in $tokensByName[$row.target]) {
                $edges[$caller].Add([pscustomobject]@{
                    Token = $callee
                    Offset = $row.il_offset
                    Opcode = $row.opcode
                })
            }
        }
        elseif ($row.target -notlike 'System.*' -and $row.target -notlike 'UnityEngine.*') {
            if (-not $unresolved.ContainsKey($caller)) { $unresolved[$caller] = 0 }
            $unresolved[$caller]++
        }
    }

    foreach ($start in $starts) {
        $queue = [System.Collections.Generic.Queue[int]]::new()
        $depth = @{}
        $previous = @{}
        $queue.Enqueue($start)
        $depth[$start] = 0
        $unknownEdges = 0
        $limitedNodes = 0
        while ($queue.Count -gt 0) {
            $current = $queue.Dequeue()
            if ($unresolved.ContainsKey($current)) { $unknownEdges += $unresolved[$current] }
            if ($current -eq $target) { continue }
            if ($depth[$current] -ge $MaxDepth) {
                if ($edges.ContainsKey($current) -and $edges[$current].Count -gt 0) { $limitedNodes++ }
                continue
            }
            if (-not $edges.ContainsKey($current)) { continue }
            foreach ($edge in $edges[$current]) {
                if ($depth.ContainsKey($edge.Token)) { continue }
                $depth[$edge.Token] = $depth[$current] + 1
                $previous[$edge.Token] = [pscustomobject]@{
                    Token = $current
                    Offset = $edge.Offset
                    Opcode = $edge.Opcode
                }
                $queue.Enqueue($edge.Token)
            }
        }

        $found = $depth.ContainsKey($target)
        $deepest = ($depth.Values | Measure-Object -Maximum).Maximum
        Write-Output ('START=0x{0:X8} TARGET=0x{1:X8} FOUND={2} VISITED={3} MAX_DEPTH={4} DEEPEST={5} LIMITED_NODES={6} UNRESOLVED_EVENTS={7}' -f $start, $target, $found.ToString().ToLowerInvariant(), $depth.Count, $MaxDepth, $deepest, $limitedNodes, $unknownEdges)
        if (-not $found) { continue }
        $path = [System.Collections.Generic.List[int]]::new()
        for ($at = $target; ; $at = $previous[$at].Token) {
            $path.Add($at)
            if ($at -eq $start) { break }
        }
        for ($index = $path.Count - 1; $index -ge 0; $index--) {
            $at = $path[$index]
            if ($at -eq $start) {
                Write-Output ('PATH=0x{0:X8} {1}' -f $at, $nameByToken[$at])
            }
            else {
                $via = $previous[$at]
                Write-Output ('PATH=0x{0:X8} {1} VIA={2}@{3}' -f $at, $nameByToken[$at], $via.Opcode, $via.Offset)
            }
        }
    }
}
finally {
    if ($pe) { $pe.Dispose() }
    $stream.Dispose()
}
