# sign_all.ps1 - signs and verifies all PC Guard executables.
#
# OV / EV certificate (installed in the Windows cert store or on a USB token):
#   .\sign_all.ps1 -Subject "Your Certificate Subject Name"
#   .\sign_all.ps1 -Thumbprint "ABCDEF123456..."
#
# Azure Artifact Signing (cloud):
#   .\sign_all.ps1 -DlibPath "C:\path\Azure.CodeSigning.Dlib.dll" -MetadataPath "C:\path\metadata.json"

param(
    [string]$DistDir = "C:\SecurityCameraSystem\ai\pc_guard\dist",
    [string]$SignTool = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe",
    [string]$Subject,
    [string]$Thumbprint,
    [string]$DlibPath,
    [string]$MetadataPath,
    [string]$TimestampUrl
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $SignTool)) { throw "signtool not found at $SignTool" }
if (-not (Test-Path $DistDir))  { throw "dist folder not found at $DistDir" }

$files = @(
    "capture_worker.exe",
    "dashboard.exe",
    "monitor.exe",
    "setup_wizard.exe",
    "tray_app.exe"
) | ForEach-Object { Join-Path $DistDir $_ }

foreach ($f in $files) {
    if (-not (Test-Path $f)) { throw "Missing file: $f" }
}

# Build the signing arguments for the chosen route
if ($DlibPath -and $MetadataPath) {
    if (-not $TimestampUrl) { $TimestampUrl = "http://timestamp.acs.microsoft.com" }
    $signArgs = @("sign", "/v", "/fd", "SHA256", "/tr", $TimestampUrl, "/td", "SHA256",
                  "/dlib", $DlibPath, "/dmdf", $MetadataPath)
}
elseif ($Subject -or $Thumbprint) {
    if (-not $TimestampUrl) { $TimestampUrl = "http://timestamp.digicert.com" }
    $signArgs = @("sign", "/v", "/fd", "SHA256", "/tr", $TimestampUrl, "/td", "SHA256")
    if ($Thumbprint) { $signArgs += @("/sha1", $Thumbprint) }
    else             { $signArgs += @("/n", $Subject) }
}
else {
    throw "Provide -Subject or -Thumbprint (OV/EV cert), or -DlibPath and -MetadataPath (Azure Artifact Signing)."
}

# Sign
foreach ($f in $files) {
    Write-Host "Signing $f ..." -ForegroundColor Cyan
    & $SignTool @signArgs $f
    if ($LASTEXITCODE -ne 0) { throw "Signing failed for $f" }
}

# Verify
Write-Host "`nVerifying signatures ..." -ForegroundColor Cyan
$failed = @()
foreach ($f in $files) {
    & $SignTool verify /pa /v $f | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK      $(Split-Path $f -Leaf)" -ForegroundColor Green
    } else {
        Write-Host "FAILED  $(Split-Path $f -Leaf)" -ForegroundColor Red
        $failed += $f
    }
}

if ($failed.Count -gt 0) { throw "$($failed.Count) file(s) failed verification." }
Write-Host "`nAll $($files.Count) files signed and verified." -ForegroundColor Green
