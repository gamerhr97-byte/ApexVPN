Unicode true
!include "LogicLib.nsh"
!ifndef PAYLOAD
 !error "Pass -DPAYLOAD=<directory containing updated modules>"
!endif
!ifndef OUTPUT
 !error "Pass -DOUTPUT=<update.exe>"
!endif

Name "Apex VPN 1.11.0 Quick Update"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\ShadowBox"
InstallDirRegKey HKCU "Software\ShadowBox" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
CRCCheck on
ManifestDPIAware true
ShowInstDetails show
Page instfiles
Var AppMutex

Function .onInit
 IfFileExists "$INSTDIR\installed.flag" +2 no_install
 IfFileExists "$INSTDIR\ApexVPN.exe" +2 no_install
 IfFileExists "$INSTDIR\nextapp\efficiency.py" +2 no_install
 IfFileExists "$INSTDIR\assets\apex-vpn-0.10.7.png" +2 no_install
 System::Call 'kernel32::CreateMutexW(p 0,i 0,w "Local\ShadowBoxDesktop") p.r0 ?e'
 Pop $1
 ${If} $1 = 183
  System::Call 'kernel32::CloseHandle(p r0)'
  MessageBox MB_OK|MB_ICONINFORMATION "Apex VPN must be fully closed, including its tray icon, before applying this update."
  Abort
 ${EndIf}
 StrCpy $AppMutex $0
 Return
 no_install:
  MessageBox MB_OK|MB_ICONSTOP "This update applies to the installed Apex VPN 0.10.7 base. Install that version first."
  Abort
FunctionEnd

Section "Update Apex VPN modules" Update
 SetOutPath "$INSTDIR"
 File /oname=ApexVPN.exe "${PAYLOAD}\ApexVPN.exe"
 File /oname=ApexVPN-0.10.7.exe "${PAYLOAD}\ApexVPN-0.10.7.exe"
 File /oname=ShadowBox.exe "${PAYLOAD}\ShadowBox.exe"
 File /oname=NekoRayNext.exe "${PAYLOAD}\NekoRayNext.exe"
 SetOutPath "$INSTDIR\runtime"
 File /oname=ApexVPNHost.exe "${PAYLOAD}\runtime\ApexVPNHost.exe"
 SetOutPath "$INSTDIR\nextapp"
 File /oname=__init__.py "${PAYLOAD}\nextapp\__init__.py"
 File /oname=branding.py "${PAYLOAD}\nextapp\branding.py"
 Delete "$INSTDIR\nextapp\__pycache__\__init__.cpython-313.pyc"
 Delete "$INSTDIR\nextapp\__pycache__\branding.cpython-313.pyc"
 File /oname=ui.py "${PAYLOAD}\nextapp\ui.py"
 File /oname=server_page.py "${PAYLOAD}\nextapp\server_page.py"
 File /oname=service_icons.py "${PAYLOAD}\nextapp\service_icons.py"
 File /oname=catalog_actions.py "${PAYLOAD}\nextapp\catalog_actions.py"
 File /oname=i18n.py "${PAYLOAD}\nextapp\i18n.py"
 File /oname=free_sources.py "${PAYLOAD}\nextapp\free_sources.py"
 File /oname=settings_schema.py "${PAYLOAD}\nextapp\settings_schema.py"
 File /oname=presentation.py "${PAYLOAD}\nextapp\presentation.py"
 File /oname=settings_ui.py "${PAYLOAD}\nextapp\settings_ui.py"
 File /oname=window_chrome.py "${PAYLOAD}\nextapp\window_chrome.py"
 File /oname=release_notes.py "${PAYLOAD}\nextapp\release_notes.py"
 File /oname=feedback.py "${PAYLOAD}\nextapp\feedback.py"
 File /oname=traffic_page.py "${PAYLOAD}\nextapp\traffic_page.py"
 File /oname=iconography.py "${PAYLOAD}\nextapp\iconography.py"
 File /oname=effects.py "${PAYLOAD}\nextapp\effects.py"
 Delete "$INSTDIR\nextapp\__pycache__\ui.cpython-313.pyc"
 Delete "$INSTDIR\nextapp\__pycache__\server_page.cpython-313.pyc"
 Delete "$INSTDIR\nextapp\__pycache__\service_icons.cpython-313.pyc"
 Delete "$INSTDIR\nextapp\__pycache__\catalog_actions.cpython-313.pyc"
 Delete "$INSTDIR\nextapp\__pycache__\i18n.cpython-313.pyc"
 Delete "$INSTDIR\nextapp\__pycache__\free_sources.cpython-313.pyc"
 Delete "$INSTDIR\nextapp\__pycache__\settings_schema.cpython-313.pyc"
 Delete "$INSTDIR\nextapp\__pycache__\presentation.cpython-313.pyc"
 Delete "$INSTDIR\nextapp\__pycache__\settings_ui.cpython-313.pyc"
 Delete "$INSTDIR\nextapp\__pycache__\window_chrome.cpython-313.pyc"
 Delete "$INSTDIR\nextapp\__pycache__\release_notes.cpython-313.pyc"
 Delete "$INSTDIR\nextapp\__pycache__\feedback.cpython-313.pyc"
 Delete "$INSTDIR\nextapp\__pycache__\traffic_page.cpython-313.pyc"
 Delete "$INSTDIR\nextapp\__pycache__\iconography.cpython-313.pyc"
 Delete "$INSTDIR\nextapp\__pycache__\effects.cpython-313.pyc"
 File /oname=service_checks.py "${PAYLOAD}\nextapp\service_checks.py"
 Delete "$INSTDIR\nextapp\__pycache__\service_checks.cpython-313.pyc"
 DetailPrint "Updated the server catalog and source list."
SectionEnd

Function .onInstSuccess
 MessageBox MB_OK|MB_ICONINFORMATION "Apex VPN 1.11.0 was updated. Start the app again. Your subscriptions and settings were kept."
FunctionEnd

Function .onGUIEnd
 ${If} $AppMutex != 0
  System::Call 'kernel32::CloseHandle(p $AppMutex)'
 ${EndIf}
FunctionEnd
