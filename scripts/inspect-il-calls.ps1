[CmdletBinding()]
param(
    [string]$AssemblyPath = (Join-Path $PSScriptRoot '..\analysis\generated\cpp2il\dll_il_recovery\Assembly-CSharp.dll'),
    [Parameter(Mandatory = $true)][string]$TypeName,
    [string]$StringPattern,
    [string]$TargetPattern,
    [string]$OutputPath = (Join-Path $PSScriptRoot '..\analysis\generated\m3\il-calls.tsv')
)

$ErrorActionPreference = 'Stop'
$assembly = (Resolve-Path -LiteralPath $AssemblyPath -ErrorAction Stop).Path
$output = [System.IO.Path]::GetFullPath($OutputPath)
New-Item -ItemType Directory -Path (Split-Path -Parent $output) -Force | Out-Null
if (Test-Path -LiteralPath $output) {
    throw "OutputPath already exists: $output"
}

function Get-TypeNameFromHandle {
    param($Reader, $Handle)
    switch ($Handle.Kind.ToString()) {
        'TypeReference' {
            $type = $Reader.GetTypeReference($Handle)
            return ($Reader.GetString($type.Namespace) + '.' + $Reader.GetString($type.Name))
        }
        'TypeDefinition' {
            $type = $Reader.GetTypeDefinition($Handle)
            return ($Reader.GetString($type.Namespace) + '.' + $Reader.GetString($type.Name))
        }
        default { return "[$($Handle.Kind)]" }
    }
}

function Resolve-MethodToken {
    param($Reader, [int]$Token, $OwnerByToken)
    $kind = ($Token -shr 24) -band 0xff
    $row = $Token -band 0x00ffffff
    switch ($kind) {
        0x06 {
            $handle = [System.Reflection.Metadata.Ecma335.MetadataTokens]::MethodDefinitionHandle($row)
            $method = $Reader.GetMethodDefinition($handle)
            return ($OwnerByToken[$Token] + '::' + $Reader.GetString($method.Name))
        }
        0x0a {
            $handle = [System.Reflection.Metadata.Ecma335.MetadataTokens]::MemberReferenceHandle($row)
            $member = $Reader.GetMemberReference($handle)
            return ((Get-TypeNameFromHandle $Reader $member.Parent) + '::' + $Reader.GetString($member.Name))
        }
        0x2b {
            $handle = [System.Reflection.Metadata.Ecma335.MetadataTokens]::MethodSpecificationHandle($row)
            $spec = $Reader.GetMethodSpecification($handle)
            $inner = [System.Reflection.Metadata.Ecma335.MetadataTokens]::GetToken([System.Reflection.Metadata.EntityHandle]$spec.Method)
            return (Resolve-MethodToken $Reader $inner $OwnerByToken)
        }
        default { return ('token:0x{0:X8}' -f $Token) }
    }
}

$opcodeByValue = @{}
foreach ($field in [System.Reflection.Emit.OpCodes].GetFields([System.Reflection.BindingFlags]'Public,Static')) {
    $opcode = $field.GetValue($null)
    $opcodeByValue[([int]$opcode.Value -band 0xffff)] = $opcode
}

$stream = [System.IO.File]::OpenRead($assembly)
$writer = $null
try {
    $pe = [System.Reflection.PortableExecutable.PEReader]::new($stream)
    $reader = [System.Reflection.Metadata.PEReaderExtensions]::GetMetadataReader($pe)
    $ownerByToken = @{}
    $targetHandles = @()

    foreach ($typeHandle in $reader.TypeDefinitions) {
        $type = $reader.GetTypeDefinition($typeHandle)
        $fullName = $reader.GetString($type.Namespace) + '.' + $reader.GetString($type.Name)
        foreach ($methodHandle in $type.GetMethods()) {
            $token = [System.Reflection.Metadata.Ecma335.MetadataTokens]::GetToken([System.Reflection.Metadata.EntityHandle]$methodHandle)
            $ownerByToken[$token] = $fullName
            if ($TypeName -eq '*' -or $fullName -eq $TypeName) { $targetHandles += $methodHandle }
        }
    }

    if ($targetHandles.Count -eq 0) { throw "Type not found or has no methods: $TypeName" }

    $writer = [System.IO.StreamWriter]::new($output, $false, [System.Text.UTF8Encoding]::new($false))
    $writer.WriteLine('method_token' + "`t" + 'method_name' + "`t" + 'il_offset' + "`t" + 'opcode' + "`t" + 'target')
    $eventCount = 0

    foreach ($methodHandle in $targetHandles) {
        $method = $reader.GetMethodDefinition($methodHandle)
        if ($method.RelativeVirtualAddress -eq 0) { continue }
        $methodToken = [System.Reflection.Metadata.Ecma335.MetadataTokens]::GetToken([System.Reflection.Metadata.EntityHandle]$methodHandle)
        $methodName = $reader.GetString($method.Name)
        $bytes = [System.Reflection.Metadata.PEReaderExtensions]::GetMethodBody($pe, $method.RelativeVirtualAddress).GetILBytes()
        $position = 0

        while ($position -lt $bytes.Length) {
            $offset = $position
            $opcodeValue = [int]$bytes[$position]
            $position++
            if ($opcodeValue -eq 0xfe) {
                if ($position -ge $bytes.Length) { throw "Truncated opcode in $methodName" }
                $opcodeValue = 0xfe00 -bor [int]$bytes[$position]
                $position++
            }
            if (-not $opcodeByValue.ContainsKey($opcodeValue)) {
                throw ('Unknown IL opcode 0x{0:X4} in {1}' -f $opcodeValue, $methodName)
            }
            $opcode = $opcodeByValue[$opcodeValue]
            $operandKind = $opcode.OperandType.ToString()
            $operandSize = switch ($operandKind) {
                'InlineNone' { 0 }
                { $_ -in @('ShortInlineBrTarget', 'ShortInlineI', 'ShortInlineVar') } { 1 }
                'InlineVar' { 2 }
                { $_ -in @('InlineBrTarget', 'InlineField', 'InlineI', 'InlineMethod', 'InlineSig', 'InlineString', 'InlineTok', 'InlineType', 'ShortInlineR') } { 4 }
                { $_ -in @('InlineI8', 'InlineR') } { 8 }
                'InlineSwitch' {
                    if ($position + 4 -gt $bytes.Length) { throw "Truncated switch in $methodName" }
                    4 + 4 * [System.BitConverter]::ToInt32($bytes, $position)
                }
                default { throw "Unsupported operand kind: $operandKind" }
            }
            if ($position + $operandSize -gt $bytes.Length) { throw "Truncated operand in $methodName" }

            $target = $null
            if ($opcode.Name -in @('call', 'callvirt', 'newobj', 'ldftn', 'ldvirtftn')) {
                $token = [System.BitConverter]::ToInt32($bytes, $position)
                $target = Resolve-MethodToken $reader $token $ownerByToken
            }
            elseif ($opcode.Name -eq 'ldstr') {
                $token = [System.BitConverter]::ToInt32($bytes, $position)
                $handle = [System.Reflection.Metadata.Ecma335.MetadataTokens]::UserStringHandle($token -band 0x00ffffff)
                $target = $reader.GetUserString($handle)
            }

            if ($StringPattern -and ($opcode.Name -ne 'ldstr' -or $target -notmatch $StringPattern)) {
                $target = $null
            }
            if ($TargetPattern -and $target -notmatch $TargetPattern) {
                $target = $null
            }
            if ($null -ne $target) {
                $safeTarget = ($target -replace '[\r\n\t]', ' ')
                $writer.WriteLine(('0x{0:X8}' -f $methodToken) + "`t" + $methodName + "`t" + ('0x{0:X4}' -f $offset) + "`t" + $opcode.Name + "`t" + $safeTarget)
                $eventCount++
            }
            $position += $operandSize
        }
    }

    Write-Output "Methods in target type: $($targetHandles.Count)"
    Write-Output "Call/string events: $eventCount"
    Write-Output "Trace: $output"
}
finally {
    if ($writer) { $writer.Dispose() }
    if ($pe) { $pe.Dispose() }
    $stream.Dispose()
}
