#include <Windows.h>
#include <cstdint>
#include <fstream>
#include <string>
#include <vector>
#include <cstring>
#include <mutex>
#include <atomic>

#include <safetyhook.hpp>

#include "SDK/Basic.hpp"
#include "SDK/CoreUObject_classes.hpp"
#include "SDK/Engine_classes.hpp"
#include "SDK/UMG_classes.hpp"

HMODULE exeModule = GetModuleHandle(NULL);
HMODULE thisModule;
std::ofstream logFile;

// Separate plain function (no C++ objects with destructors) so __try/__except is legal.
bool TryReadStackQword(uintptr_t* stackPtr, int index, uintptr_t* outVal)
{
    __try
    {
        *outVal = stackPtr[index];
        return true;
    }
    __except (EXCEPTION_EXECUTE_HANDLER)
    {
        return false;
    }
}

// SEH-wrapped call to SetJustification -- if this specific call crashes immediately
// (as opposed to corrupting something that crashes later elsewhere), this catches it
// and the game survives instead of dying. Defense in depth on top of the delayed-hook
// fix; doesn't help with delayed/indirect corruption, but costs nothing and covers the
// immediate-crash case outright.
// Only calls SetJustification if the value actually needs to change. The sweep runs
// every 2s indefinitely and re-checks thousands of widgets that are already correctly
// set after the first pass -- calling the UFUNCTION unconditionally on all of them,
// forever, means thousands of redundant Invalidate()/layout-dirty calls per cycle.
// A crash after ~12,000+ successful sweep cycles (not on the first one) is consistent
// with that kind of slow-building overhead/corruption, not an immediate logic bug.
// Returns 1 if it actually wrote a change, 0 if already correct (no-op), -1 on SEH fault.
int TrySetJustificationRight(SDK::UTextLayoutWidget* tb, int32_t offset)
{
    __try
    {
        uint8_t current = *reinterpret_cast<uint8_t*>(reinterpret_cast<uint8_t*>(tb) + offset);
        if (current == static_cast<uint8_t>(SDK::ETextJustify::Right))
            return 0; // already correct, nothing to do

        tb->SetJustification(SDK::ETextJustify::Right);
        return 1;
    }
    __except (EXCEPTION_EXECUTE_HANDLER)
    {
        return -1;
    }
}

LONG WINAPI CrashDiagnosticHandler(EXCEPTION_POINTERS* info)
{
    DWORD code = info->ExceptionRecord->ExceptionCode;
    // Only care about real crashes, not benign single-step/breakpoint noise.
    if (code != EXCEPTION_ACCESS_VIOLATION && code != EXCEPTION_ILLEGAL_INSTRUCTION &&
        code != EXCEPTION_STACK_OVERFLOW && code != EXCEPTION_ARRAY_BOUNDS_EXCEEDED &&
        code != EXCEPTION_INT_DIVIDE_BY_ZERO && code != EXCEPTION_PRIV_INSTRUCTION)
        return EXCEPTION_CONTINUE_SEARCH;

    auto* ctx = info->ContextRecord;
    auto* rec = info->ExceptionRecord;
    uintptr_t addr = reinterpret_cast<uintptr_t>(rec->ExceptionAddress);
    uintptr_t exeBase = reinterpret_cast<uintptr_t>(exeModule);
    uintptr_t thisBase = reinterpret_cast<uintptr_t>(thisModule);

    std::ofstream crashLog;
    CHAR gameExePath[MAX_PATH] = { 0 };
    GetModuleFileNameA(exeModule, gameExePath, MAX_PATH);
    std::string exeDir(gameExePath);
    exeDir = exeDir.substr(0, exeDir.find_last_of("\\/"));
    crashLog.open((exeDir + "\\OctopathArabicRTL_CRASH.log").c_str(), std::ios::trunc);

    crashLog << "=== CRASH DETECTED ===" << std::endl;
    crashLog << "ExceptionCode: 0x" << std::hex << code << std::endl;
    crashLog << "ExceptionAddress: 0x" << addr << std::endl;
    crashLog << "exeModule base: 0x" << exeBase << " -> crash at exe+0x" << (addr - exeBase) << std::endl;
    if (addr >= thisBase && thisBase != 0)
        crashLog << "thisModule (our DLL) base: 0x" << thisBase << " -> crash at ours+0x" << (addr - thisBase) << std::endl;
    else
        crashLog << "Crash address is NOT inside our DLL (thisModule base 0x" << thisBase << ")" << std::endl;

    if (code == EXCEPTION_ACCESS_VIOLATION && rec->NumberParameters >= 2)
    {
        crashLog << "Access violation " << (rec->ExceptionInformation[0] ? "WRITE" : "READ")
                  << " at address 0x" << rec->ExceptionInformation[1] << std::endl;
    }

    crashLog << std::dec;
    crashLog << "RIP=0x" << std::hex << ctx->Rip << " RSP=0x" << ctx->Rsp << " RBP=0x" << ctx->Rbp << std::endl;
    crashLog << "RAX=0x" << ctx->Rax << " RBX=0x" << ctx->Rbx << " RCX=0x" << ctx->Rcx << " RDX=0x" << ctx->Rdx << std::endl;
    crashLog << "RSI=0x" << ctx->Rsi << " RDI=0x" << ctx->Rdi << " R8=0x" << ctx->R8 << " R9=0x" << ctx->R9 << std::endl;

    // Minimal stack walk: dump raw qwords near RSP -- return addresses often visible
    // even without proper unwinding, useful to see which module called into the crash.
    crashLog << "Stack dump near RSP:" << std::endl;
    auto* stackPtr = reinterpret_cast<uintptr_t*>(ctx->Rsp);
    for (int i = 0; i < 32; ++i)
    {
        uintptr_t val = 0;
        if (!TryReadStackQword(stackPtr, i, &val))
        {
            crashLog << "  (stack read faulted, stopped early)" << std::endl;
            break;
        }
        crashLog << "  [RSP+0x" << std::hex << (i * 8) << "] = 0x" << val;
        if (val >= exeBase) crashLog << "  (exe+0x" << (val - exeBase) << ")";
        if (thisBase != 0 && val >= thisBase && val < thisBase + 0x200000) crashLog << "  (OURS+0x" << (val - thisBase) << ")";
        crashLog << std::endl;
    }

    crashLog << "=== END CRASH DIAGNOSTIC ===" << std::endl;
    crashLog.flush();
    crashLog.close();

    return EXCEPTION_CONTINUE_SEARCH; // let the crash proceed normally after logging
}

namespace Memory
{
    std::vector<int> PatternToBytes(const char* pattern)
    {
        auto bytes = std::vector<int>{};
        auto start = const_cast<char*>(pattern);
        auto end = const_cast<char*>(pattern) + strlen(pattern);

        for (auto current = start; current < end; ++current) {
            if (*current == '?') {
                ++current;
                if (*current == '?')
                    ++current;
                bytes.push_back(-1);
            }
            else {
                bytes.push_back(strtoul(current, &current, 16));
            }
        }
        return bytes;
    }

    std::uint8_t* PatternScan(void* module, const char* signature)
    {
        auto dosHeader = reinterpret_cast<PIMAGE_DOS_HEADER>(module);
        auto ntHeaders = reinterpret_cast<PIMAGE_NT_HEADERS>(reinterpret_cast<std::uint8_t*>(module) + dosHeader->e_lfanew);
        size_t sizeOfImage = ntHeaders->OptionalHeader.SizeOfImage;

        auto patternBytes = PatternToBytes(signature);
        auto scanBytes = reinterpret_cast<std::uint8_t*>(module);

        size_t s = patternBytes.size();
        auto* d = patternBytes.data();

        for (size_t i = 0; i < sizeOfImage - s; ++i)
        {
            bool found = true;
            for (size_t j = 0; j < s; ++j)
            {
                if (scanBytes[i + j] != d[j] && d[j] != -1)
                {
                    found = false;
                    break;
                }
            }
            if (found)
                return &scanBytes[i];
        }
        return nullptr;
    }

    std::uint8_t* GetRelativeAddr(std::uint8_t* address) noexcept
    {
        if (!address) return nullptr;
        std::int32_t offset = *reinterpret_cast<std::int32_t*>(address);
        return address + sizeof(offset) + offset;
    }
}

static SafetyHookMid ProcessEventMidHook{};
static std::uint8_t* g_processEventAddr = nullptr;
static thread_local bool bInHook = false;
static std::atomic<SDK::UFunction*> g_cachedSetTextFunc{nullptr};
static std::atomic<SDK::UClass*> g_cachedKSTextBlockClass{nullptr};
static std::atomic<int32_t> g_justificationOffset{-1}; // -1 = not resolved / not found
static std::atomic<int> g_hitCount{0};
static std::mutex g_logMutex;

// UE4SS-style "GetPropertyByNameInChain": walk ChildProperties (FField linked list)
// for THIS struct, then its SuperStruct, etc. -- respects the object's REAL inheritance,
// unlike the SDK's generated SetJustification() wrapper which hardcodes a literal
// ancestor class name ("TextLayoutWidget") that KSTextBlock does not have.
int32_t FindPropertyOffsetInChain(SDK::UStruct* strct, const char* propName)
{
    for (SDK::UStruct* s = strct; s; s = s->SuperStruct)
    {
        for (SDK::FField* field = s->ChildProperties; field; field = field->Next)
        {
            if (field->Name.ToString() == propName)
            {
                auto* prop = reinterpret_cast<SDK::FProperty*>(field);
                return prop->Offset;
            }
        }
    }
    return -1;
}

// Hot path: pure pointer comparison + direct byte write. No ProcessEvent, no UFunction
// lookup -- avoids the null-Function crash entirely.
void ProcessEventHook(SafetyHookContext& ctx)
{
    if (bInHook) return;
    if (!ctx.rcx || !ctx.rdx) return;

    auto* func = reinterpret_cast<SDK::UFunction*>(ctx.rdx);
    SDK::UFunction* cached = g_cachedSetTextFunc.load(std::memory_order_acquire);
    if (!cached || func != cached) return;

    int32_t offset = g_justificationOffset.load(std::memory_order_relaxed);
    if (offset < 0) return;

    SDK::UClass* cachedClass = g_cachedKSTextBlockClass.load(std::memory_order_relaxed);
    if (!cachedClass) return;

    bInHook = true;

    auto* obj = reinterpret_cast<SDK::UObject*>(ctx.rcx);
    // "SetText" may be inherited by OTHER classes too (shared UFunction* across the
    // hierarchy) -- IsA() confirms this object is actually KSTextBlock-derived before
    // we touch it.
    if (obj && obj->Class && obj->Class->Class && obj->IsA(cachedClass))
    {
        // Usmap ground truth confirms TextLayoutWidget IS KSTextBlock's real superclass,
        // so the SDK's generated wrapper (Class->GetFunction("TextLayoutWidget",
        // "SetJustification")) should genuinely find the function this time. Going through
        // the real UFUNCTION call (not a raw offset write) so Slate's own invalidation/
        // repaint logic fires -- a raw byte write wouldn't trigger a visual update even
        // if it succeeded.
        auto* tb = static_cast<SDK::UTextLayoutWidget*>(obj);
        int result = TrySetJustificationRight(tb, offset);

        int n = g_hitCount.fetch_add(1) + 1;
        if (n <= 10)
        {
            std::lock_guard<std::mutex> lock(g_logMutex);
            logFile << "SetJustification result=" << result << " #" << n << std::endl;
            logFile.flush();
        }
    }

    bInHook = false;
}

// Sweeps GObjects directly for every existing KSTextBlock instance and patches it.
// This sidesteps the race entirely: instead of trying to catch a one-time SetText
// call before it happens (which we keep losing since KSTextBlock isn't even
// registered in GObjects until ~2.4s into boot, by which point many widgets already
// got their one-time SetText call), we just fix whatever currently exists, on a
// repeating timer, so newly-opened menus get caught by later sweeps too.
void SweepAndPatchAllKSTextBlocks(SDK::UClass* cls, int32_t offset)
{
    auto* arr = SDK::UObject::GObjects.GetTypedPtr();
    if (!arr) return;

    int total = arr->Num();
    int patched = 0;
    int checked = 0;
    for (int i = 0; i < total; ++i)
    {
        SDK::UObject* obj = arr->GetByIndex(i);
        if (!obj || !obj->Class || !obj->Class->Class) continue;
        if (!obj->IsA(cls)) continue;

        checked++;
        auto* tb = static_cast<SDK::UTextLayoutWidget*>(obj);
        if (TrySetJustificationRight(tb, offset) == 1) patched++;
    }

    if (patched > 0)
    {
        std::lock_guard<std::mutex> lock(g_logMutex);
        logFile << "Sweep: checked " << checked << ", actually wrote " << patched
                 << " (rest already correct)." << std::endl;
        logFile.flush();
    }
}

DWORD __stdcall SweepLoopThread(void*)
{
    for (;;)
    {
        Sleep(2000);
        SDK::UClass* cls = g_cachedKSTextBlockClass.load(std::memory_order_relaxed);
        int32_t offset = g_justificationOffset.load(std::memory_order_relaxed);
        if (cls && offset >= 0)
            SweepAndPatchAllKSTextBlocks(cls, offset);
    }
}

// Runs on a background thread, retrying until the KSTextBlock class (and its SetText
// function/Justification property) is registered -- it may not exist in GObjects yet
// at DLL-init time.
DWORD __stdcall ResolveTargetFunctionThread(void*)
{
    for (int attempt = 0; attempt < 300; ++attempt) // up to 30s
    {
        SDK::UClass* cls = SDK::UObject::FindClassFast("KSTextBlock");
        if (cls)
        {
            SDK::UFunction* func = cls->GetFunction("TextBlock", "SetText");
            if (!func)
                func = cls->GetFunction("KSTextBlock", "SetText");

            int32_t justOffset = FindPropertyOffsetInChain(cls, "Justification");

            if (func && justOffset >= 0)
            {
                // Store class+offset BEFORE func: the hot path gates on func being
                // non-null first, so by the time it observes that, class+offset must
                // already be visible.
                g_cachedKSTextBlockClass.store(cls, std::memory_order_relaxed);
                g_justificationOffset.store(justOffset, std::memory_order_relaxed);
                g_cachedSetTextFunc.store(func, std::memory_order_release);
                std::lock_guard<std::mutex> lock(g_logMutex);
                logFile << "Resolved KSTextBlock::SetText UFunction* and Justification offset 0x"
                        << std::hex << justOffset << std::dec
                        << " after " << attempt << " attempts." << std::endl;
                logFile.flush();

                // Immediately sweep existing instances (covers everything constructed
                // during the race window before this resolved), then keep sweeping
                // periodically to catch newly-opened menus/screens.
                SweepAndPatchAllKSTextBlocks(cls, justOffset);
                HANDLE sweepHandle = CreateThread(NULL, 0, SweepLoopThread, 0, NULL, 0);
                if (sweepHandle) CloseHandle(sweepHandle);

                return 0;
            }
            else if (func && justOffset < 0)
            {
                std::lock_guard<std::mutex> lock(g_logMutex);
                logFile << "SetText resolved but NO 'Justification' property found anywhere in KSTextBlock's chain." << std::endl;
                logFile.flush();
                return 1;
            }
        }
        Sleep(100);
    }

    std::lock_guard<std::mutex> lock(g_logMutex);
    logFile << "FAILED to resolve KSTextBlock class/function after 30s." << std::endl;
    logFile.flush();
    return 1;
}

void UpdateOffsetsAndHook()
{
    // GObjects (identical signature to Octopath0Fix's proven working scan)
    std::uint8_t* GObjectsScanResult = Memory::PatternScan(exeModule, "48 8B ?? ?? ?? ?? ?? 48 8B ?? ?? 48 8D ?? ?? EB ?? 33 ?? 8B ?? ?? C1 ??");
    if (GObjectsScanResult) {
        std::uint8_t* GObjectsAddr = Memory::GetRelativeAddr(GObjectsScanResult + 0x3);
        SDK::Offsets::GObjects = static_cast<int32_t>(GObjectsAddr - reinterpret_cast<std::uint8_t*>(exeModule));
        logFile << "GObjects: 0x" << std::hex << SDK::Offsets::GObjects << std::endl;
    }
    else {
        logFile << "GObjects: pattern scan FAILED" << std::endl;
        return;
    }

    // AppendString (required for FName::ToString()/GetName() to work -- without it,
    // FName::InitInternal() computes a garbage function pointer and crashes on first call)
    std::uint8_t* AppendStringScanResult = Memory::PatternScan(exeModule, "48 8D ?? ?? ?? 48 89 ?? ?? ?? E8 ?? ?? ?? ?? 83 ?? ?? ?? 00 48 8D ?? ?? ?? ?? ?? 41 ?? 01 00 00 00 48 8B ??");
    if (AppendStringScanResult) {
        std::uint8_t* AppendStringAddr = Memory::GetRelativeAddr(AppendStringScanResult + 0xB);
        SDK::Offsets::AppendString = static_cast<int32_t>(AppendStringAddr - reinterpret_cast<std::uint8_t*>(exeModule));
        logFile << "AppendString: 0x" << std::hex << SDK::Offsets::AppendString << std::endl;
    }
    else {
        logFile << "AppendString: pattern scan FAILED" << std::endl;
        return;
    }

    // ProcessEvent -- resolve the address now (safe, just reading exe bytes), but
    // DON'T install the hook yet. praydog/UEVR (a mature ProcessEvent-hooking mod
    // supporting hundreds of UE games, using the same SafetyHook library) explicitly
    // installs its ProcessEvent hook LAZILY, not during initial DLL activation, to
    // avoid "early-game instability". Our repeated identical-signature crashes are
    // consistent with hooking this extremely hot, high-concurrency function too early,
    // before the engine has finished booting.
    std::uint8_t* ProcessEventScanResult = Memory::PatternScan(exeModule, "40 ?? 56 57 41 ?? 41 ?? 41 ?? 41 ?? 48 81 ?? ?? ?? ?? ?? 48 8D ?? ?? ?? 48 89 ?? ?? ?? ?? ?? 48 8B ?? ?? ?? ?? ?? 48 33 ?? 48 89 ?? ?? ?? ?? ?? 4D 8B ??");
    if (ProcessEventScanResult) {
        SDK::Offsets::ProcessEvent = static_cast<int32_t>(ProcessEventScanResult - reinterpret_cast<std::uint8_t*>(exeModule));
        logFile << "ProcessEvent: 0x" << std::hex << SDK::Offsets::ProcessEvent << std::endl;

        // Our 8 consecutive identical-signature crashes (regardless of hook logic,
        // timing, or SEH protection) match a documented SafetyHook limitation:
        // relocating RIP-relative instructions in a function's prologue can fail if a
        // trampoline can't be placed correctly relative to them. Bytes 0-18 of this
        // pattern are pure register pushes + "sub rsp, imm32" (no RIP-relative
        // addressing at all); byte ~19 onward looks like a stack-cookie security check
        // using RIP-relative loads. Hooking at +19 lets SafetyHook relocate only the
        // safe push/sub instructions, entirely avoiding the suspect ones -- and RCX/RDX
        // (This/Function) are untouched by pushes or "sub rsp", so they're still valid.
        g_processEventAddr = ProcessEventScanResult + 19;
    }
    else {
        logFile << "ProcessEvent: pattern scan FAILED" << std::endl;
    }
}

DWORD __stdcall DelayedHookInstallThread(void*)
{
    // The delayed-install experiment confirmed the crash was NOT actually about timing
    // (the +19 offset fix is what stopped the crashes) -- but delaying until
    // Engine+GameViewport meant we missed every widget's ONE-TIME SetText call that
    // happened during early boot, before the hook was active. Installing as soon as
    // the address is resolved instead, now that the offset fix makes early hooking safe.
    if (!g_processEventAddr)
    {
        std::lock_guard<std::mutex> lock(g_logMutex);
        logFile << "ProcessEvent address never resolved, cannot install hook." << std::endl;
        logFile.flush();
        return 1;
    }

    ProcessEventMidHook = safetyhook::create_mid(g_processEventAddr, ProcessEventHook);
    std::lock_guard<std::mutex> lock(g_logMutex);
    logFile << "ProcessEvent hook installed (immediate, offset+19)." << std::endl;
    logFile.flush();
    return 0;
}

DWORD __stdcall Main(void*)
{
    CHAR gameExePath[MAX_PATH] = { 0 };
    GetModuleFileNameA(exeModule, gameExePath, MAX_PATH);
    std::string exeDir(gameExePath);
    exeDir = exeDir.substr(0, exeDir.find_last_of("\\/"));

    logFile.open((exeDir + "\\OctopathArabicRTL.log").c_str(), std::ios::trunc);
    logFile << "OctopathArabicRTL starting..." << std::endl;

    AddVectoredExceptionHandler(1, CrashDiagnosticHandler);
    logFile << "Crash diagnostic handler installed." << std::endl;

    UpdateOffsetsAndHook();

    logFile << "Init complete." << std::endl;
    logFile.flush();

    HANDLE resolverHandle = CreateThread(NULL, 0, ResolveTargetFunctionThread, 0, NULL, 0);
    if (resolverHandle) CloseHandle(resolverHandle);

    HANDLE delayedHookHandle = CreateThread(NULL, 0, DelayedHookInstallThread, 0, NULL, 0);
    if (delayedHookHandle) CloseHandle(delayedHookHandle);

    return true;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved)
{
    switch (ul_reason_for_call)
    {
    case DLL_PROCESS_ATTACH:
    {
        DisableThreadLibraryCalls(hModule);
        thisModule = hModule;

        HANDLE mainHandle = CreateThread(NULL, 0, Main, 0, NULL, 0);
        if (mainHandle)
        {
            SetThreadPriority(mainHandle, THREAD_PRIORITY_HIGHEST);
            CloseHandle(mainHandle);
        }
        break;
    }
    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
    case DLL_PROCESS_DETACH:
        break;
    }
    return TRUE;
}
