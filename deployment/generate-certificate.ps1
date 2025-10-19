# PowerShell Script to Generate Self-Signed Certificate for Code Signing
# This creates a certificate that can be used to sign your executable
# Run as Administrator

param(
    [string]$CertName = "ChatYapper",
    [string]$OutputPath = "..\dist",
    [int]$ValidYears = 5
)

Write-Host "=== Chat Yapper Certificate Generator ===" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "WARNING: Not running as Administrator. Certificate installation may fail." -ForegroundColor Yellow
    Write-Host "For best results, run this script as Administrator." -ForegroundColor Yellow
    Write-Host ""
}

# Create output directory if it doesn't exist
$OutputPath = Join-Path $PSScriptRoot $OutputPath
if (-not (Test-Path $OutputPath)) {
    New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
    Write-Host "Created output directory: $OutputPath" -ForegroundColor Green
}

# Certificate paths
$cerFile = Join-Path $OutputPath "$CertName.cer"
$pfxFile = Join-Path $OutputPath "$CertName.pfx"

# Generate a strong password for the PFX file
$pfxPassword = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 16 | ForEach-Object {[char]$_})
$securePassword = ConvertTo-SecureString -String $pfxPassword -Force -AsPlainText

Write-Host "Generating self-signed certificate..." -ForegroundColor Yellow

try {
    # Create the certificate
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject "CN=$CertName" `
        -FriendlyName "$CertName Code Signing Certificate" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -NotAfter (Get-Date).AddYears($ValidYears) `
        -KeyLength 2048 `
        -KeyAlgorithm RSA `
        -HashAlgorithm SHA256 `
        -KeyUsage DigitalSignature `
        -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3") `
        -KeyExportPolicy Exportable

    Write-Host "Certificate generated successfully!" -ForegroundColor Green
    Write-Host "  Thumbprint: $($cert.Thumbprint)" -ForegroundColor Cyan
    Write-Host "  Subject: $($cert.Subject)" -ForegroundColor Cyan
    Write-Host "  Valid Until: $($cert.NotAfter)" -ForegroundColor Cyan
    Write-Host ""

    # Export certificate to .cer file (public key only)
    Export-Certificate -Cert $cert -FilePath $cerFile -Force | Out-Null
    Write-Host "Exported public certificate to: $cerFile" -ForegroundColor Green

    # Export certificate with private key to .pfx file
    Export-PfxCertificate -Cert $cert -FilePath $pfxFile -Password $securePassword -Force | Out-Null
    Write-Host "Exported private certificate to: $pfxFile" -ForegroundColor Green
    Write-Host ""

    # Save password to a text file for reference
    $passwordFile = Join-Path $OutputPath "$CertName-password.txt"
    $pfxPassword | Out-File $passwordFile -Force
    Write-Host "PFX Password saved to: $passwordFile" -ForegroundColor Yellow
    Write-Host "  Password: $pfxPassword" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "IMPORTANT: Keep this password secure! You'll need it for code signing." -ForegroundColor Red
    Write-Host ""

    # Optionally install certificate to Trusted Root (for local testing)
    $installChoice = Read-Host "Do you want to install this certificate to your Trusted Root store? (Y/N)"
    if ($installChoice -eq 'Y' -or $installChoice -eq 'y') {
        if ($isAdmin) {
            try {
                # Install to LocalMachine Trusted Root (requires admin)
                Import-Certificate -FilePath $cerFile -CertStoreLocation "Cert:\LocalMachine\Root" | Out-Null
                Write-Host "Certificate installed to LocalMachine Trusted Root store" -ForegroundColor Green
                
                # Also install to Trusted Publishers
                Import-Certificate -FilePath $cerFile -CertStoreLocation "Cert:\LocalMachine\TrustedPublisher" | Out-Null
                Write-Host "Certificate installed to Trusted Publishers store" -ForegroundColor Green
            }
            catch {
                Write-Host "Error installing certificate: $_" -ForegroundColor Red
            }
        }
        else {
            Write-Host "Installing to CurrentUser stores (limited privileges)..." -ForegroundColor Yellow
            Import-Certificate -FilePath $cerFile -CertStoreLocation "Cert:\CurrentUser\Root" | Out-Null
            Write-Host "Certificate installed to CurrentUser Trusted Root store" -ForegroundColor Green
        }
    }

    Write-Host ""
    Write-Host "=== Certificate Generation Complete ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Use the .pfx file to sign your executable with signtool.exe" -ForegroundColor White
    Write-Host "2. Include the .cer file in your installer for user installation" -ForegroundColor White
    Write-Host "3. Keep the .pfx file and password secure!" -ForegroundColor White
    Write-Host ""
    Write-Host "Example signing command:" -ForegroundColor Cyan
    Write-Host "  signtool sign /f `"$pfxFile`" /p `"$pfxPassword`" /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 `"YourApp.exe`"" -ForegroundColor Gray
    Write-Host ""

    return @{
        Success = $true
        CertThumbprint = $cert.Thumbprint
        CerFile = $cerFile
        PfxFile = $pfxFile
        Password = $pfxPassword
    }
}
catch {
    Write-Host "Error generating certificate: $_" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    return @{
        Success = $false
        Error = $_.Exception.Message
    }
}
