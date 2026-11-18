#define UNICODE
#define _UNICODE
#include <windows.h>
#include <wchar.h>

static volatile DWORD *startup_progress=NULL;
static LRESULT CALLBACK SplashProc(HWND window,UINT message,WPARAM wparam,LPARAM lparam) {
    if(message==WM_PAINT) {
        PAINTSTRUCT ps;HDC dc=BeginPaint(window,&ps);RECT bounds;GetClientRect(window,&bounds);
        TRIVERTEX vertices[2]={{0,0,0x6500,0x0900,0x0F00,0xFF00},{320,140,0x0500,0x0500,0x0700,0xFF00}};
        GRADIENT_RECT gradient={0,1};GradientFill(dc,vertices,2,&gradient,1,GRADIENT_FILL_RECT_H);
        HICON icon=(HICON)LoadImageW(GetModuleHandleW(NULL),MAKEINTRESOURCEW(1),IMAGE_ICON,52,52,LR_DEFAULTCOLOR);
        if(icon){DrawIconEx(dc,22,30,icon,52,52,0,NULL,DI_NORMAL);DestroyIcon(icon);}
        SetBkMode(dc,TRANSPARENT);SetTextColor(dc,RGB(255,255,255));
        HFONT title=CreateFontW(-20,0,0,0,FW_SEMIBOLD,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Segoe UI");
        HFONT old=(HFONT)SelectObject(dc,title);RECT text={91,27,309,58};DrawTextW(dc,L"Apex VPN",-1,&text,DT_SINGLELINE);
        HFONT small=CreateFontW(-11,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Segoe UI");
        SelectObject(dc,small);SetTextColor(dc,RGB(226,186,192));
        DWORD progress=startup_progress?*startup_progress:0;
        const wchar_t *status=progress<30?L"Checking data folder...":progress<45?L"Checking local ports...":progress<90?L"Checking network cores...":L"Preparing interface...";
        RECT label={91,63,309,96};DrawTextW(dc,status,-1,&label,DT_WORDBREAK);
        RECT track={22,113,298,118};HBRUSH bg=CreateSolidBrush(RGB(51,22,28));FillRect(dc,&track,bg);DeleteObject(bg);
        if(progress>100)progress=100;track.right=22+(LONG)(276*progress/100);HBRUSH red=CreateSolidBrush(RGB(229,51,72));FillRect(dc,&track,red);DeleteObject(red);
        SelectObject(dc,old);DeleteObject(title);DeleteObject(small);EndPaint(window,&ps);return 0;
    }
    return DefWindowProcW(window,message,wparam,lparam);
}
static HWND splash(HINSTANCE instance) {
    WNDCLASSW wc={0};wc.lpfnWndProc=SplashProc;wc.hInstance=instance;wc.lpszClassName=L"ApexStartup";RegisterClassW(&wc);
    HWND window=CreateWindowExW(WS_EX_TOPMOST|WS_EX_TOOLWINDOW,L"ApexStartup",L"",WS_POPUP,
        (GetSystemMetrics(SM_CXSCREEN)-320)/2,(GetSystemMetrics(SM_CYSCREEN)-140)/2,320,140,NULL,NULL,instance,NULL);
    ShowWindow(window,SW_SHOWNOACTIVATE);UpdateWindow(window);return window;
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, LPWSTR args, int show) {
    HANDLE app_mutex=CreateMutexW(NULL,FALSE,L"Local\\ShadowBoxDesktop");
    if(app_mutex && GetLastError()==ERROR_ALREADY_EXISTS) {
        CloseHandle(app_mutex);
        MessageBoxW(NULL,L"Apex VPN is already running, or its installer is active. Check the system tray.",L"Apex VPN",MB_OK|MB_ICONINFORMATION);return 1;
    }
    SYSTEM_INFO info;GetNativeSystemInfo(&info);
    if (info.wProcessorArchitecture!=PROCESSOR_ARCHITECTURE_AMD64) {
        MessageBoxW(NULL,L"This build requires an x64 Intel/AMD computer and Windows 10 version 1809 or later.",L"Apex VPN",MB_OK|MB_ICONINFORMATION);return 2;
    }
    // RtlGetVersion reports the true OS version even without compatibility shims.
    typedef LONG (WINAPI *VersionFunction)(OSVERSIONINFOW*);
    VersionFunction version=(VersionFunction)GetProcAddress(GetModuleHandleW(L"ntdll.dll"),"RtlGetVersion");
    OSVERSIONINFOW os={0};os.dwOSVersionInfoSize=sizeof(os);
    if (!version || version(&os)!=0 || os.dwMajorVersion<10 || os.dwBuildNumber<17763) {
        MessageBoxW(NULL,L"Windows 10 version 1809 (build 17763) or later is required. Windows 7/8 cannot run this Qt 6 build.",L"Apex VPN",MB_OK|MB_ICONINFORMATION);return 2;
    }
    wchar_t base[32768], python[32768], command[32768], event_name[128];
    DWORD n=GetModuleFileNameW(NULL,base,32768);
    if (!n || n>=32768) return 2;
    wchar_t *slash=wcsrchr(base,L'\\');if (!slash) return 2;*slash=0;
    if (wcslen(base)>15000) return 2;
    swprintf(python,32768,L"%ls\\runtime\\ApexVPNHost.exe",base);
    swprintf(command,32768,L"\"%ls\" \"%ls\\app.py\"",python,base);
    swprintf(event_name,128,L"Local\\ShadowBoxReady-%lu",GetCurrentProcessId());
    HANDLE ready=CreateEventW(NULL,TRUE,FALSE,event_name);
    SetEnvironmentVariableW(L"SHADOW_BOX_READY_EVENT",event_name);
    wchar_t mapping_name[128];swprintf(mapping_name,128,L"Local\\ApexStartup-%lu",GetCurrentProcessId());
    HANDLE mapping=CreateFileMappingW(INVALID_HANDLE_VALUE,NULL,PAGE_READWRITE,0,4,mapping_name);
    if(mapping)startup_progress=(DWORD*)MapViewOfFile(mapping,FILE_MAP_ALL_ACCESS,0,0,4);
    if(startup_progress)*startup_progress=0;
    SetEnvironmentVariableW(L"APEX_VPN_STARTUP_MAP",mapping_name);
    HWND loading=splash(instance);
    STARTUPINFOW start={0};start.cb=sizeof(start);PROCESS_INFORMATION process={0};
    if (!CreateProcessW(python,command,NULL,NULL,FALSE,0,NULL,base,&start,&process)) {
        DestroyWindow(loading);if(ready)CloseHandle(ready);
        MessageBoxW(NULL,L"Could not start Apex VPN. Reinstall the complete application; its bundled runtime must be present.",L"Apex VPN",MB_OK|MB_ICONERROR);return 3;
    }
    CloseHandle(process.hThread);
    DWORD began=GetTickCount(),painted=0;MSG message;
    while(WaitForSingleObject(process.hProcess,loading?20:INFINITE)==WAIT_TIMEOUT) {
        while(PeekMessageW(&message,NULL,0,0,PM_REMOVE)){TranslateMessage(&message);DispatchMessageW(&message);}
        if(loading && startup_progress && *startup_progress!=painted){painted=*startup_progress;InvalidateRect(loading,NULL,FALSE);UpdateWindow(loading);}
        if(loading && GetTickCount()-began>=1000 && ((ready && WaitForSingleObject(ready,0)==WAIT_OBJECT_0)||GetTickCount()-began>30000)) {DestroyWindow(loading);loading=NULL;}
    }
    if(loading)DestroyWindow(loading);if(ready)CloseHandle(ready);
    if(startup_progress)UnmapViewOfFile((void*)startup_progress);if(mapping)CloseHandle(mapping);
    DWORD code=1;GetExitCodeProcess(process.hProcess,&code);CloseHandle(process.hProcess);return (int)code;
}
