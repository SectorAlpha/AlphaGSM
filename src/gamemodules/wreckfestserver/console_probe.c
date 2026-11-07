/* Capture a fresh native Wreckfest Tracks response in a private Wine prefix.
 * Build for Windows; this observer never starts or stops the game server.
 */
#ifndef UNICODE
#define UNICODE 1
#endif
#ifndef _UNICODE
#define _UNICODE 1
#endif
#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <shellapi.h>
#include <tlhelp32.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

#define WIDTH 256
#define HEIGHT 4096
#define CELLS (WIDTH * HEIGHT)
#define CAPTURE_MS 30000

static int fail(HANDLE file, const char *step)
{
    DWORD written;
    if (file != INVALID_HANDLE_VALUE)
        WriteFile(file, step, (DWORD)strlen(step), &written, NULL);
    return 1;
}

static DWORD selected_process(const WCHAR *expected)
{
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    PROCESSENTRY32W entry;
    DWORD found = 0;
    unsigned int matches = 0;
    if (snapshot == INVALID_HANDLE_VALUE) return 0;
    ZeroMemory(&entry, sizeof(entry));
    entry.dwSize = sizeof(entry);
    if (Process32FirstW(snapshot, &entry)) do
    {
        HANDLE process;
        WCHAR path[32768];
        DWORD size = 32768;
        if (_wcsicmp(entry.szExeFile, L"Wreckfest_x64.exe") &&
            _wcsicmp(entry.szExeFile, L"Wreckfest.exe")) continue;
        process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, entry.th32ProcessID);
        if (!process) continue;
        if (QueryFullProcessImageNameW(process, 0, path, &size) && !_wcsicmp(path, expected))
        {
            found = entry.th32ProcessID;
            matches++;
        }
        CloseHandle(process);
    } while (Process32NextW(snapshot, &entry));
    CloseHandle(snapshot);
    return matches == 1 ? found : 0;
}

static int write_rows(HANDLE file, const WCHAR *buffer)
{
    unsigned int row, last_cell = CELLS, last_row;
    DWORD written;
    /* Wreckfest redraws its input prompt at a saved cursor position while the
     * registry prints. The live cursor can therefore precede fresh output.
     * Every cell was blanked before tracks, so the last nonblank cell is the
     * fresh display boundary; no old screen rows can enter this capture.
     */
    while (last_cell && (buffer[last_cell - 1] == L' ' || buffer[last_cell - 1] == L'\0')) last_cell--;
    last_row = last_cell ? (last_cell - 1) / WIDTH : 0;
    for (row = 0; row <= last_row && row < HEIGHT; row++)
    {
        const WCHAR *line = buffer + row * WIDTH;
        int length = WIDTH, bytes;
        char encoded[WIDTH * 4 + 1];
        while (length && line[length - 1] == L' ') length--;
        bytes = WideCharToMultiByte(CP_UTF8, 0, line, length, encoded, sizeof(encoded), NULL, NULL);
        if (length && (!bytes || !WriteFile(file, encoded, (DWORD)bytes, &written, NULL) || written != (DWORD)bytes))
            return 1;
        if (!WriteFile(file, "\n", 1, &written, NULL) || written != 1) return 1;
    }
    return 0;
}

static int capture(HANDLE file, const WCHAR *executable)
{
    const WCHAR command[] = L"tracks\r";
    INPUT_RECORD keys[(sizeof(command) / sizeof(command[0]) - 1) * 2];
    HANDLE output, input;
    CONSOLE_SCREEN_BUFFER_INFO info;
    COORD origin = {0, 0}, size = {WIDTH, HEIGHT};
    DWORD pid = selected_process(executable), count;
    WCHAR *buffer, *previous_buffer;
    ULONGLONG deadline, stable_since = 0;
    int result = 1;
    BOOL read_ok = FALSE;
    unsigned int i;
    if (!pid) return fail(file, "Native capture failed: expected exactly one matching Wreckfest executable\n");
    FreeConsole();
    if (!AttachConsole(pid)) return fail(file, "Native capture failed: AttachConsole\n");
    output = CreateFileW(L"CONOUT$", GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE,
                         NULL, OPEN_EXISTING, 0, NULL);
    input = CreateFileW(L"CONIN$", GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE,
                        NULL, OPEN_EXISTING, 0, NULL);
    if (output == INVALID_HANDLE_VALUE || input == INVALID_HANDLE_VALUE)
    {
        fail(file, "Native capture failed: console handles\n");
        goto cleanup;
    }
    /* This is the disposable test server's console. Blank its display before
     * requesting the registry so old screen contents can never satisfy proof.
     */
    if (!SetConsoleScreenBufferSize(output, size) ||
        !FillConsoleOutputCharacterW(output, L' ', CELLS, origin, &count) || count != CELLS ||
        !SetConsoleCursorPosition(output, origin))
    {
        fail(file, "Native capture failed: fresh console boundary\n");
        goto cleanup;
    }
    ZeroMemory(keys, sizeof(keys));
    for (i = 0; i < sizeof(command) / sizeof(command[0]) - 1; i++)
    {
        keys[i * 2].EventType = KEY_EVENT;
        keys[i * 2].Event.KeyEvent.bKeyDown = TRUE;
        keys[i * 2].Event.KeyEvent.wRepeatCount = 1;
        keys[i * 2].Event.KeyEvent.wVirtualKeyCode = command[i] == L'\r' ? VK_RETURN : (WORD)(command[i] - L'a' + L'A');
        keys[i * 2].Event.KeyEvent.uChar.UnicodeChar = command[i];
        keys[i * 2 + 1] = keys[i * 2];
        keys[i * 2 + 1].Event.KeyEvent.bKeyDown = FALSE;
    }
    if (!WriteConsoleInputW(input, keys, sizeof(keys) / sizeof(keys[0]), &count) ||
        count != sizeof(keys) / sizeof(keys[0]))
    {
        fail(file, "Native capture failed: fixed tracks input\n");
        goto cleanup;
    }
    buffer = calloc(CELLS + 1, sizeof(WCHAR));
    if (!buffer) goto cleanup;
    previous_buffer = calloc(CELLS + 1, sizeof(WCHAR));
    if (!previous_buffer) { free(buffer); goto cleanup; }
    deadline = GetTickCount64() + CAPTURE_MS;
    while (GetTickCount64() < deadline)
    {
        if (!GetConsoleScreenBufferInfo(output, &info) || info.dwSize.X != WIDTH || info.dwSize.Y != HEIGHT ||
            !ReadConsoleOutputCharacterW(output, buffer, CELLS, origin, &count) || count != CELLS)
            break;
        read_ok = TRUE;
        if (memcmp(buffer, previous_buffer, CELLS * sizeof(WCHAR)))
        {
            memcpy(previous_buffer, buffer, CELLS * sizeof(WCHAR));
            stable_since = GetTickCount64();
        }
        if (wcsstr(buffer, L"Tracks:") && GetTickCount64() - stable_since >= 1000)
        {
            result = 0;
            break;
        }
        Sleep(100);
    }
    if (read_ok && write_rows(file, buffer)) result = 1;
    free(previous_buffer);
    free(buffer);
    if (result) fail(file, "Native capture failed: no complete fresh Tracks response before deadline\n");
cleanup:
    if (output != INVALID_HANDLE_VALUE) CloseHandle(output);
    if (input != INVALID_HANDLE_VALUE) CloseHandle(input);
    FreeConsole();
    return result;
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR command_line, int show)
{
    WCHAR **args;
    HANDLE file;
    int argc, result;
    (void)instance; (void)previous; (void)command_line; (void)show;
    args = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (!args || argc != 3) return 2;
    /* CREATE_NEW makes a prior evidence file an error instead of a cache. */
    file = CreateFileW(args[2], GENERIC_WRITE, FILE_SHARE_READ, NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) { LocalFree(args); return 3; }
    result = capture(file, args[1]);
    CloseHandle(file);
    LocalFree(args);
    return result;
}
