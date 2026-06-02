$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrEmpty($ScriptDir)) {
    $ScriptDir = Get-Location
}

$WshShell = New-Object -ComObject WScript.Shell
$ShortcutPath = Join-Path $ScriptDir "Sincronizar_JG_Store.lnk"
$BatPath = Join-Path $ScriptDir "Sincronizar_JG_Store.bat"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $BatPath
$Shortcut.WorkingDirectory = $ScriptDir
# Usamos el icono de las flechas de sincronización verdes de shell32.dll (index 238)
$Shortcut.IconLocation = "C:\Windows\System32\shell32.dll, 238"
$Shortcut.Description = "Sincronizador JG-Store - Coronel Mayorista"
$Shortcut.Save()
