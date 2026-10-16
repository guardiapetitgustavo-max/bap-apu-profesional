#define MyAppName "BAP APU Profesional"
#define MyAppVersion "1.4.0"
#define MyAppPublisher "BAP Soluciones Tecnológicas"
#define MyAppURL "https://bap-soluciones-tecnologicas.quick-spark-9180.chatgpt.site"
#define MyAppExeName "BAP_APU_Profesional.exe"
[Setup]
AppId={{A9D590C9-823B-4C8E-8E29-8A9A510A0100}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\BAP APU Profesional
DefaultGroupName={#MyAppName}
OutputBaseFilename=Instalador_BAP_APU_Profesional_1.4.0
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
SetupIconFile=..\assets\bap_apu.ico
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
[Files]
Source: "..\dist\BAP_APU_Profesional\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
