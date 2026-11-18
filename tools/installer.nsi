Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "WinVer.nsh"
!include "x64.nsh"
!ifndef PAYLOAD
 !error "Pass -DPAYLOAD=<staged app folder>"
!endif
!ifndef OUTPUT
 !error "Pass -DOUTPUT=<installer.exe>"
!endif
Name "Apex VPN 0.10.7"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\ShadowBox"
InstallDirRegKey HKCU "Software\ShadowBox" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID zlib
CRCCheck on
ManifestDPIAware true
VIProductVersion "0.10.7.0"
VIAddVersionKey "ProductName" "Apex VPN"
VIAddVersionKey "FileDescription" "Apex VPN Offline Setup"
VIAddVersionKey "FileVersion" "0.10.7.0"
VIAddVersionKey "ProductVersion" "0.10.7"
VIAddVersionKey "LegalCopyright" "Apex VPN contributors; GPL-3.0"
!define MUI_ICON "../assets/apex-vpn.ico"
!define MUI_UNICON "../assets/apex-vpn.ico"
!define MUI_BGCOLOR "FFF5F6"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TEXT "Install Apex VPN for your Windows account.$\r$\n$\r$\nPython, Qt, Xray and runtime dependencies are included. No internet or administrator access is required.$\r$\n$\r$\nRequires Windows 10 1809+ or Windows 11 on an Intel/AMD x64 computer. Windows 7/8 and ARM are not supported.$\r$\n$\r$\nPlease close Apex VPN before upgrading."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "../LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\ApexVPN.exe"
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchInstalled
!define MUI_FINISHPAGE_RUN_TEXT "Start Apex VPN"
!insertmacro MUI_PAGE_FINISH
!define MUI_UNCONFIRMPAGE_TEXT_TOP "خجالت نمیکشی ؟ لذتتو بردیو گفتی برم ! پاک کن ولی خجالت بکش ! 🥺🥺 چجوری دلت میاد آخه !"
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Farsi"
Var AppMutex

Function .onInit
 ${IfNot} ${AtLeastWin10}
  MessageBox MB_OK|MB_ICONINFORMATION "This build requires Windows 10 version 1809 or later. Windows 7/8 cannot run its Qt 6 runtime."
  Abort
 ${EndIf}
 ${IfNot} ${IsNativeAMD64}
  MessageBox MB_OK|MB_ICONINFORMATION "This installer supports Intel/AMD x64 PCs only. A separate build is needed for 32-bit or ARM Windows."
  Abort
 ${EndIf}
 SetRegView 64
 ReadRegStr $0 HKLM "SOFTWARE\Microsoft\Windows NT\CurrentVersion" "CurrentBuildNumber"
 ${If} $0 < 17763
  MessageBox MB_OK|MB_ICONINFORMATION "Windows 10 build 17763 (1809) or later is required."
  Abort
 ${EndIf}
 System::Call 'kernel32::CreateMutexW(p 0,i 0,w "Local\ShadowBoxDesktop") p.r0 ?e'
 Pop $1
 ${If} $1 = 183
  System::Call 'kernel32::CloseHandle(p r0)'
  MessageBox MB_OK|MB_ICONINFORMATION "Close Apex VPN completely (including the tray icon), then run Setup again."
  Abort
 ${EndIf}
 ; Hold the same mutex throughout installation, so a running app cannot be overwritten.
 StrCpy $AppMutex $0
FunctionEnd

Function LaunchInstalled
 System::Call 'kernel32::CloseHandle(p $AppMutex)'
 StrCpy $AppMutex 0
 Exec '"$INSTDIR\ApexVPN.exe"'
FunctionEnd

Section "Apex VPN (offline runtime included)" Core
 SectionIn RO
 SetOutPath "$INSTDIR"
 Delete "$INSTDIR\portable.flag"
 Delete "$INSTDIR\ApexVPN-0.10.6.exe"
 Delete "$INSTDIR\ApexVPN-0.10.5.exe"
 Delete "$INSTDIR\ApexVPN-0.10.4.exe"
 File /r "${PAYLOAD}/*"
 WriteUninstaller "$INSTDIR\Uninstall.exe"
 SetRegView 64
 WriteRegStr HKCU "Software\ShadowBox" "InstallDir" "$INSTDIR"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBox" "DisplayName" "Apex VPN"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBox" "DisplayVersion" "0.10.7"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBox" "DisplayIcon" "$INSTDIR\ApexVPN.exe,0"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBox" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBox" "QuietUninstallString" '$\"$INSTDIR\Uninstall.exe$\" /S'
 WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBox" "NoModify" 1
 WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBox" "NoRepair" 1
 CreateDirectory "$SMPROGRAMS\Apex VPN"
 CreateShortcut "$SMPROGRAMS\Apex VPN\Apex VPN.lnk" "$INSTDIR\ApexVPN.exe" "" "$INSTDIR\ApexVPN.exe" 0
 CreateShortcut "$SMPROGRAMS\Apex VPN\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\App Paths\vpn.exe" "" "$INSTDIR\ApexVPN.exe"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\App Paths\vpn.exe" "Path" "$INSTDIR"
SectionEnd

Section "Desktop shortcut"
 Delete "$DESKTOP\Shadow Box.lnk"
 CreateShortcut "$DESKTOP\Apex VPN.lnk" "$INSTDIR\ApexVPN.exe" "" "$INSTDIR\ApexVPN.exe" 0
SectionEnd

Function .onGUIEnd
 ${If} $AppMutex != 0
  System::Call 'kernel32::CloseHandle(p $AppMutex)'
 ${EndIf}
FunctionEnd

Function un.onInit
 System::Call 'kernel32::CreateMutexW(p 0,i 0,w "Local\ShadowBoxDesktop") p.r0 ?e'
 Pop $1
 ${If} $1 = 183
  System::Call 'kernel32::CloseHandle(p r0)'
  MessageBox MB_OK|MB_ICONINFORMATION "Close Apex VPN, including its tray icon, before uninstalling."
  Abort
 ${EndIf}
FunctionEnd

Section "Uninstall"
 ; Only owned application files: user profiles remain in LocalAppData\NekoRayNext.
 !include "uninstall-files.nsh"
 Delete "$INSTDIR\Uninstall.exe"
 RMDir "$INSTDIR"
 Delete "$DESKTOP\Shadow Box.lnk"
 Delete "$DESKTOP\Apex VPN.lnk"
 Delete "$SMPROGRAMS\Apex VPN\Apex VPN.lnk"
 Delete "$SMPROGRAMS\Apex VPN\Uninstall.lnk"
 RMDir "$SMPROGRAMS\Apex VPN"
 SetRegView 64
 DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBox"
 DeleteRegKey HKCU "Software\ShadowBox"
 DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\App Paths\vpn.exe"
SectionEnd
