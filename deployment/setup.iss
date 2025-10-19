; Inno Setup Script for Chat Yapper
; This script creates a Windows installer that:
; - Installs the application to Program Files
; - Creates Start Menu shortcuts
; - Optionally installs a self-signed certificate for code signing
; - Handles uninstallation properly

#define MyAppName "Chat Yapper"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ChatYapper Dev"
#define MyAppURL "https://github.com/pladisdev/chat-yapper"
#define MyAppExeName "ChatYapper.exe"
#define MyAppID "{A5F8C9D2-E1B3-4F6A-9C7D-2E8F1B4A6C9D}"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
AppId={{#MyAppID}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
; Uncomment the following line if you have an icon
; SetupIconFile=..\assets\icon.ico
OutputDir=..\dist\installer
OutputBaseFilename=ChatYapper-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}
; Code signing (uncomment and configure if you have a certificate)
; SignTool=signtool
; SignedUninstaller=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode
Name: "installcert"; Description: "Install self-signed certificate (allows the application to run without security warnings)"; GroupDescription: "Security:"; Flags: unchecked

[Files]
; Main executable
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Self-signed certificate (if exists)
Source: "..\dist\ChatYapper.cer"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall; Tasks: installcert; Check: FileExists(ExpandConstant('{src}\..\dist\ChatYapper.cer'))
; Additional files (add your assets, configs, etc.)
; Source: "..\dist\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
; Source: "..\dist\config\*"; DestDir: "{app}\config"; Flags: ignoreversion
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Dirs]
; Create directories for user data
Name: "{userappdata}\{#MyAppName}"; Permissions: users-modify
Name: "{userappdata}\{#MyAppName}\logs"; Permissions: users-modify
Name: "{userappdata}\{#MyAppName}\audio"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Install certificate to Trusted Root if user selected the option
Filename: "certutil.exe"; Parameters: "-addstore -f ""TrustedPublisher"" ""{tmp}\ChatYapper.cer"""; Flags: runhidden; StatusMsg: "Installing certificate..."; Tasks: installcert; Check: FileExists(ExpandConstant('{tmp}\ChatYapper.cer'))
Filename: "certutil.exe"; Parameters: "-addstore -f ""Root"" ""{tmp}\ChatYapper.cer"""; Flags: runhidden; StatusMsg: "Installing certificate to trusted root..."; Tasks: installcert; Check: FileExists(ExpandConstant('{tmp}\ChatYapper.cer'))
; Launch application after install (optional)
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Remove certificate on uninstall if it was installed
Filename: "certutil.exe"; Parameters: "-delstore ""TrustedPublisher"" ""ChatYapper"""; Flags: runhidden; RunOnceId: "RemoveCertPublisher"
Filename: "certutil.exe"; Parameters: "-delstore ""Root"" ""ChatYapper"""; Flags: runhidden; RunOnceId: "RemoveCertRoot"

[Code]
function FileExists(const FileName: string): Boolean;
begin
  Result := FileOrDirExists(FileName);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Add any post-install tasks here
    Log('Installation completed successfully');
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Clean up user data (optional - you might want to keep logs)
    // DelTree(ExpandConstant('{userappdata}\{#MyAppName}'), True, True, True);
    Log('Uninstallation completed');
  end;
end;
