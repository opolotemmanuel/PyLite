[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$PythonPath,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PyLiteArguments
)
if (-not $PythonPath) {
    $pythonCommand = Get-Command python -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pythonCommand) { $PythonPath = $pythonCommand.Source }
}
if (-not $PythonPath) {
    Write-Error 'Python 3.10+ was not found. Pass -PythonPath with the path to python.exe.'
    exit 1
}
# ProcessStartInfo avoids PowerShell's legacy native-argument quote stripping.
# ArgumentList is available in PowerShell 7; Windows PowerShell 5.1 needs CRT quoting.
function ConvertTo-NativeArgument([string]$Value) {
    $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}
$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $PythonPath
$startInfo.WorkingDirectory = $PSScriptRoot
$startInfo.UseShellExecute = $false
$arguments = @('-m', 'pylite') + @($PyLiteArguments)
if ($null -ne $startInfo.PSObject.Properties['ArgumentList']) {
    foreach ($argument in $arguments) { $startInfo.ArgumentList.Add($argument) }
} else {
    $startInfo.Arguments = ($arguments | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' '
}
$process = New-Object System.Diagnostics.Process
$process.StartInfo = $startInfo
try {
    [void]$process.Start()
    $process.WaitForExit()
    $result = $process.ExitCode
} catch {
    Write-Error "Could not launch Python '$PythonPath': $_"
    $result = 1
} finally {
    $process.Dispose()
}
exit $result
