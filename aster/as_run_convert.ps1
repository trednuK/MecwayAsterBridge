# as_run_convert.ps1 V5
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$distro = "Ubuntu"
Write-Host "AS_RUN_WRAPPER_V5"
Write-Host "Distribution: $distro"

function ConvertTo-WslPath([string]$Path) {
    $p = $Path.TrimEnd('\', '/')
    if ($p -match '^([A-Za-z]):[\\/](.*)$') {
        $drive = $Matches[1].ToLower()
        $rest = ($Matches[2] -replace '\\', '/').Trim('/')
        if ($rest) { return "/mnt/$drive/$rest" }
        return "/mnt/$drive"
    }
    return ($p -replace '\\', '/')
}

function Convert-OnePath([string]$Raw, [string]$CwdNorm) {
    $norm = ($Raw.TrimEnd('\', '/')) -replace '/', '\'
    if ($norm.StartsWith($CwdNorm + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        return ($norm.Substring($CwdNorm.Length + 1) -replace '\\', '/')
    }
    if ($norm.Equals($CwdNorm, [System.StringComparison]::OrdinalIgnoreCase)) {
        return "."
    }
    Write-Host "WARNUNG: Pfad ausserhalb des Arbeitsverzeichnisses: $Raw"
    return ($Raw -replace '\\', '/')
}

function Convert-ExportContent([string]$Content, [string]$Cwd) {
    $cwdNorm = $Cwd.TrimEnd('\', '/')
    $pattern = '(?i)[A-Za-z]:[\\/][^\s''"]+'
    $lines = $Content -split "`r`n|`n|`r"
    $out = New-Object System.Collections.Generic.List[string]
    foreach ($line in $lines) {
        $matches = [regex]::Matches($line, $pattern)
        if ($matches.Count -eq 0) {
            $out.Add($line)
            continue
        }
        $sb = New-Object System.Text.StringBuilder
        $idx = 0
        foreach ($m in $matches) {
            [void]$sb.Append($line.Substring($idx, $m.Index - $idx))
            [void]$sb.Append((Convert-OnePath $m.Value $cwdNorm))
            $idx = $m.Index + $m.Length
        }
        if ($idx -lt $line.Length) {
            [void]$sb.Append($line.Substring($idx))
        }
        $out.Add($sb.ToString())
    }
    return ($out -join "`n")
}

$cwd = (Get-Location).Path
$wslCwd = ConvertTo-WslPath $cwd
Write-Host "Arbeitsverzeichnis: $cwd"
Write-Host "WSL-Arbeitsverzeichnis: $wslCwd"

$exportFile = $null
$otherArgs = New-Object System.Collections.Generic.List[string]
foreach ($arg in $Arguments) {
    if (-not $exportFile -and $arg -like "*.export") {
        $exportFile = $arg
    } else {
        [void]$otherArgs.Add($arg)
    }
}

$tempName = $null
$caveArgs = New-Object System.Collections.Generic.List[string]
foreach ($a in $otherArgs) { [void]$caveArgs.Add($a) }

if ($exportFile) {
    $fullExport = $exportFile
    if (-not [System.IO.Path]::IsPathRooted($fullExport)) {
        $fullExport = Join-Path $cwd $exportFile
    }
    if (-not (Test-Path -LiteralPath $fullExport)) {
        Write-Host "FEHLER: Export-Datei nicht gefunden: $fullExport"
        exit 2
    }

    Write-Host "Konvertiere: $fullExport"
    $content = [System.IO.File]::ReadAllText($fullExport)
    $content = Convert-ExportContent $content $cwd
    if (-not $content.EndsWith("`n")) { $content += "`n" }

    $tempName = "as_run_temp.export"
    $tempExport = Join-Path $cwd $tempName
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($tempExport, $content, $utf8)
    [void]$caveArgs.Add($tempName)

    Write-Host "---- Pfade in der temporaeren Export-Datei ----"
    foreach ($line in ($content -split "`n")) {
        if ($line -match '^[A-Za-z]') { Write-Host $line }
    }
}

if ($caveArgs.Count -eq 0) {
    Write-Host "FEHLER: Keine Argumente."
    exit 2
}

Write-Host "Starte: wsl -d $distro --cd $wslCwd cave run -- $($caveArgs -join ' ')"
& wsl.exe -d $distro --cd $wslCwd cave run -- @caveArgs
$exitCode = $LASTEXITCODE
if ($null -eq $exitCode) { $exitCode = 1 }

if ($tempName) {
    $tempExport = Join-Path $cwd $tempName
    if (Test-Path -LiteralPath $tempExport) {
        Remove-Item -LiteralPath $tempExport -Force
    }
}

exit $exitCode
