#define AppName "Collectivité LANTCHIBLE"
#define AppVersion "1.0.0"

[Setup]
AppId={{0C7C8512-9A5F-4F9B-BD1E-57F0A3B2C7D1}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\Collectivité LANTCHIBLE
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
Uninstallable=yes
OutputDir=Output
OutputBaseFilename=SolidariteEtoile_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis supplémentaires :"; Flags: unchecked

[Files]
Source: "..\dist\SolidariteEtoile\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Collectivité LANTCHIBLE"; Filename: "{app}\SolidariteEtoile.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Collectivité LANTCHIBLE"; Filename: "{app}\SolidariteEtoile.exe"; WorkingDir: "{app}"; Tasks: desktopicon
