[CmdletBinding()]
param(
    [byte[]]$Seed = @(0x31, 0x22, 0x7F),
    [byte]$Shift = 0x0B,
    [byte]$LogicalCommand = 0x16,
    [ValidateRange(0, 255)]
    [int]$ReceiveIndex = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($Seed.Count -eq 0) {
    throw 'Seed must contain at least one byte.'
}

[byte[]]$effectiveKey = [byte[]]::new($Seed.Count)
$prefix = 0
for ($index = 0; $index -lt $Seed.Count; $index++) {
    $prefix = $prefix -bxor [int]$Seed[$index]
    $effectiveKey[$index] = [byte]$prefix
}

$normalizedIndex = $ReceiveIndex % $effectiveKey.Count
$keyByte = [int]$effectiveKey[$normalizedIndex]
$rawCommand = [byte]((((([int]$LogicalCommand + [int]$Shift) -band 0xFF)) -bxor $keyByte))
$decodedCommand = [byte]((((([int]$rawCommand -bxor $keyByte) - [int]$Shift)) -band 0xFF))

if ($decodedCommand -ne $LogicalCommand) {
    throw 'Command transform did not round-trip.'
}

$testKeys = @(0x00, 0x01, 0x5A, 0xFF)
$casesChecked = 0
foreach ($testKey in $testKeys) {
    for ($testShift = 0; $testShift -lt 256; $testShift++) {
        for ($testCommand = 0; $testCommand -lt 256; $testCommand++) {
            $encoded = (((($testCommand + $testShift) -band 0xFF)) -bxor $testKey)
            $decoded = (((($encoded -bxor $testKey) - $testShift)) -band 0xFF)
            if ($decoded -ne $testCommand) {
                throw "Inverse check failed for command=$testCommand shift=$testShift key=$testKey."
            }
            $casesChecked++
        }
    }
}

[pscustomobject]@{
    SeedHex = ($Seed | ForEach-Object { '{0:X2}' -f $_ }) -join ' '
    EffectiveKeyHex = ($effectiveKey | ForEach-Object { '{0:X2}' -f $_ }) -join ' '
    ShiftHex = '{0:X2}' -f $Shift
    ReceiveIndex = $normalizedIndex
    LogicalCommandHex = '{0:X2}' -f $LogicalCommand
    RawCommandHex = '{0:X2}' -f $rawCommand
    DecodedCommandHex = '{0:X2}' -f $decodedCommand
    NextReceiveIndex = ($normalizedIndex + 1) % $effectiveKey.Count
    InverseCasesChecked = $casesChecked
}
