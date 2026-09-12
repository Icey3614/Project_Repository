$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$srcDir = Join-Path $root 'src'
$outExe = Join-Path $root 'PoemWidget.exe'
$manifest = Join-Path $root 'app.manifest'
$iconPath = Join-Path $root 'icon.ico'

$csc = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path $csc)) { $csc = 'C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe' }

# ---- generate a simple icon for the exe/tray ----
Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap 32, 32
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = 'AntiAlias'
$g.Clear([System.Drawing.Color]::Transparent)
$path = New-Object System.Drawing.Drawing2D.GraphicsPath
$path.AddArc(1,1,16,16,180,90)
$path.AddArc(15,1,16,16,270,90)
$path.AddArc(15,15,16,16,0,90)
$path.AddArc(1,15,16,16,90,90)
$path.CloseFigure()
$seal = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(220,150,40,40))
$g.FillPath($seal, $path)
$font = New-Object System.Drawing.Font('KaiTi', 21, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$white = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
$sf = New-Object System.Drawing.StringFormat
$sf.Alignment = 'Center'
$sf.LineAlignment = 'Center'
$g.DrawString('诗', $font, $white, (New-Object System.Drawing.RectangleF 0,0,32,32), $sf)
$g.Dispose(); $font.Dispose(); $white.Dispose(); $seal.Dispose(); $path.Dispose(); $sf.Dispose()
$iconObj = [System.Drawing.Icon]::FromHandle($bmp.GetHicon())
$iconStream = [System.IO.File]::Open($iconPath, [System.IO.FileMode]::Create)
$iconObj.Save($iconStream)
$iconStream.Close()
$iconObj.Dispose(); $bmp.Dispose()

# ---- references ----
$fw = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319'
$refs = @(
  (Join-Path $fw 'WPF\WindowsBase.dll'),
  (Join-Path $fw 'WPF\PresentationCore.dll'),
  (Join-Path $fw 'WPF\PresentationFramework.dll'),
  (Join-Path $fw 'WPF\PresentationUI.dll'),
  (Join-Path $fw 'System.Xaml.dll'),
  (Join-Path $fw 'System.Windows.Forms.dll'),
  (Join-Path $fw 'System.Drawing.dll'),
  (Join-Path $fw 'System.Web.Extensions.dll')
)

$args = @(
  '/nologo',
  '/target:winexe',
  '/platform:anycpu',
  '/optimize+',
  "/out:$outExe",
  "/win32manifest:$manifest",
  "/win32icon:$iconPath"
)
foreach ($r in $refs) { $args += "/reference:$r" }
$sources = Get-ChildItem (Join-Path $srcDir '*.cs') | ForEach-Object { $_.FullName }
$args += $sources

Write-Host ("Building -> {0}" -f $outExe)
& $csc $args
if ($LASTEXITCODE -ne 0) {
  Write-Error ("csc failed with exit code {0}" -f $LASTEXITCODE)
}
Write-Host "Build OK: $outExe"
