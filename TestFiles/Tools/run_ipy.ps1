# Runs an IronPython script with Mecway's IronPython 2.7.9, without Mecway
# (check of Python 2.7 compatibility and offscreen GUI tests).
# Usage:
#   powershell -ExecutionPolicy Bypass -File run_ipy.ps1 -Script <path.py> -ScriptArgs a,b
#   & .\run_ipy.ps1 -Script <path.py> -ScriptArgs a,b      (from PowerShell itself)
# With -File PowerShell passes "a,b" as one string; a single argument that
# contains commas is therefore split into separate arguments (so an argument
# that itself contains a comma cannot be passed on its own).
# Exit code: 0 = OK, 1 = exception in the script (traceback printed after the
# output of the script), n = sys.exit(n).
param([string]$Script, [string[]]$ScriptArgs)
$mw = "C:\Program Files\Mecway"
foreach ($d in "Microsoft.Scripting","Microsoft.Dynamic","IronPython","IronPython.Modules") {
    Add-Type -Path (Join-Path $mw "$d.dll")
}
$Script = (Resolve-Path $Script).Path
$argList = @()
foreach ($a in $ScriptArgs) {
    if ($ScriptArgs.Count -eq 1 -and $a.Contains(",")) {
        $argList += $a.Split(",")
    } else {
        $argList += $a
    }
}
$engine = [IronPython.Hosting.Python]::CreateEngine()
$paths = $engine.GetSearchPaths()
$paths.Add("$mw\IronPython.2.7.9\Lib")
$paths.Add((Split-Path $Script))
$engine.SetSearchPaths($paths)
$out = New-Object System.IO.MemoryStream
# UTF-8 without BOM (otherwise the output starts with U+FEFF)
$utf8 = New-Object System.Text.UTF8Encoding $false
$engine.Runtime.IO.SetOutput($out, $utf8)
$engine.Runtime.IO.SetErrorOutput($out, $utf8)
$sys = [IronPython.Hosting.Python]::GetSysModule($engine)
$argv = New-Object IronPython.Runtime.List
$argv.append($Script)
foreach ($a in $argList) { $argv.append($a) }
$sys.SetVariable("argv", $argv)
$code = 0
$errorText = $null
try {
    $engine.ExecuteFile($Script) | Out-Null
} catch {
    # PowerShell wraps the .NET exception (MethodInvocationException).
    $ex = $_.Exception
    while ($ex.InnerException -ne $null -and
           $ex -is [System.Management.Automation.MethodInvocationException]) {
        $ex = $ex.InnerException
    }
    if ($ex -is [IronPython.Runtime.Exceptions.SystemExitException]) {
        # sys.exit(n): n becomes the exit code (None -> 0, other object -> 1)
        $other = $null
        $code = $ex.GetExitCode([ref]$other)
    } else {
        # ScriptEngine.GetService<ExceptionOperations>() is a generic method
        # that PowerShell 5.1 cannot call directly: call it via reflection.
        $get = [Microsoft.Scripting.Hosting.ScriptEngine].GetMethod("GetService")
        $get = $get.MakeGenericMethod([Microsoft.Scripting.Hosting.ExceptionOperations])
        $eo = $get.Invoke($engine, @(, [object[]]@()))
        $errorText = "ERROR: " + $eo.FormatException($ex)
        $code = 1
    }
}
$utf8.GetString($out.ToArray())
if ($errorText) { Write-Output $errorText }
exit $code
