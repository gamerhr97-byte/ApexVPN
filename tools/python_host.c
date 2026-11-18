#define UNICODE
#define _UNICODE
#include <windows.h>
#include <shellapi.h>
#include <wchar.h>

/* Own Windows process identity while using the bundled CPython DLL in-process. */
int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, LPWSTR args, int show) {
    wchar_t library[32768];
    DWORD length = GetModuleFileNameW(NULL, library, 32768);
    if (!length || length >= 32740) return 2;
    wchar_t *slash = wcsrchr(library, L'\\');
    if (!slash) return 2;
    wcscpy(slash + 1, L"python313.dll");
    HMODULE python = LoadLibraryExW(library, NULL,
        LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    if (!python) {
        MessageBoxW(NULL, L"The bundled Python runtime could not load. Reinstall Apex VPN using its complete Setup EXE.",
            L"Apex VPN", MB_OK | MB_ICONERROR);
        return 3;
    }
    typedef int (__cdecl *PythonMain)(int, wchar_t **);
    PythonMain run = (PythonMain)GetProcAddress(python, "Py_Main");
    if (!run) return 4;
    int count = 0;
    wchar_t **arguments = CommandLineToArgvW(GetCommandLineW(), &count);
    if (!arguments) return 5;
    int status = run(count, arguments);
    LocalFree(arguments);
    /* CPython extensions can retain DLL references at shutdown. Let OS unload. */
    return status;
}
