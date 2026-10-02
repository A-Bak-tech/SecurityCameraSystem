param(
    [string]$PcGuardDir = "C:\SecurityCameraSystem\ai\pc_guard",
    [string]$MakeAppx   = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\makeappx.exe"
)

$ErrorActionPreference = "Stop"

$dist     = Join-Path $PcGuardDir "dist"
$stage    = Join-Path $PcGuardDir "msix_staging"
$assets   = Join-Path $stage "Assets"
$manifest = Join-Path $PcGuardDir "AppxManifest.xml"
$icon     = Join-Path $PcGuardDir "pcguard_icon.ico"
$output   = Join-Path $PcGuardDir "PCGuard_1.0.0.0_x64.msix"

$exes = "tray_app.exe","dashboard.exe","setup_wizard.exe","monitor.exe","capture_worker.exe"

if (-not (Test-Path $MakeAppx)) { throw "makeappx.exe not found at $MakeAppx" }
if (-not (Test-Path $manifest)) { throw "AppxManifest.xml not found at $manifest" }
if (-not (Test-Path $icon))     { throw "Icon not found at $icon" }
foreach ($e in $exes) {
    if (-not (Test-Path (Join-Path $dist $e))) { throw "Missing $e in $dist" }
}

if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Path $assets -Force | Out-Null

foreach ($e in $exes) { Copy-Item (Join-Path $dist $e) $stage }
Get-ChildItem $PcGuardDir -Filter *.onnx | ForEach-Object { Copy-Item $_.FullName $stage }
Copy-Item $manifest (Join-Path $stage "AppxManifest.xml")

python -m pip install pillow --quiet
$pyFile = Join-Path $env:TEMP "make_msix_assets.py"
@"
import os
from PIL import Image
icon = r'$icon'
out = r'$assets'
im = Image.open(icon).convert('RGBA')
for name, size in [('StoreLogo', 50), ('Square44x44Logo', 44), ('Square150x150Logo', 150)]:
    im.resize((size, size), Image.LANCZOS).save(os.path.join(out, name + '.png'))
"@ | Set-Content -Path $pyFile -Encoding UTF8
python $pyFile
if ($LASTEXITCODE -ne 0) { throw "Asset generation failed" }

& $MakeAppx pack /d $stage /p $output /o
if ($LASTEXITCODE -ne 0) { throw "makeappx failed" }

Write-Host "`nCreated $output" -ForegroundColor Green