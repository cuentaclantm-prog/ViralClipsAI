#define MyAppName "ViralClips AI"
#define MyAppVersion "1.0.0"
[Setup]
AppId={{7A0A3B0D-6D1D-4D90-92D4-1E5B08C1D910}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\ViralClips AI
DefaultGroupName=ViralClips AI
OutputDir=installer
OutputBaseFilename=ViralClipsAI_Setup_Windows10_64bit
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
[Files]
Source: "dist\ViralClipsAI\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
[Icons]
Name: "{autoprograms}\ViralClips AI"; Filename: "{app}\ViralClipsAI.exe"
Name: "{autodesktop}\ViralClips AI"; Filename: "{app}\ViralClipsAI.exe"
[Run]
Filename: "{app}\ViralClipsAI.exe"; Description: "Abrir ViralClips AI"; Flags: postinstall nowait skipifsilent
