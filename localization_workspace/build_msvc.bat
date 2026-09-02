@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

set SRC=C:\Users\faisa\Ai\Mods Dev\OctopathTraveler0\localization_workspace\Octopath0Fix_src
set OUT=C:\Users\faisa\Ai\Mods Dev\OctopathTraveler0\localization_workspace\msvc_build
mkdir "%OUT%" 2>nul

set CXXFLAGS=/std:c++latest /EHsc /nologo /MT /O2 /DZYDIS_STATIC_BUILD /DZYCORE_STATIC_BUILD /DSAFETYHOOK_STATIC_DEFINE /DNOMINMAX /DWIN32_LEAN_AND_MEAN
set CFLAGS=/nologo /MT /O2 /DZYDIS_STATIC_BUILD /DZYCORE_STATIC_BUILD

set INC=/I"%SRC%\src" /I"%SRC%\external\safetyhook\include" /I"%SRC%\external\zydis\include" /I"%SRC%\external\zydis\dependencies\zycore\include"

echo === Compiling zycore ===
for %%f in ("%SRC%\external\zydis\dependencies\zycore\src\*.c") do (
  cl.exe %CFLAGS% %INC% /c "%%f" /Fo"%OUT%\zycore_%%~nf.obj" || goto :error
)

echo === Compiling zydis ===
for %%f in ("%SRC%\external\zydis\src\*.c") do (
  cl.exe %CFLAGS% %INC% /I"%SRC%\external\zydis\src" /c "%%f" /Fo"%OUT%\zydis_%%~nf.obj" || goto :error
)

echo === Assembling mid_hook ASM ===
"C:\Users\faisa\AppData\Local\bin\NASM\nasm.exe" -f win64 "%SRC%\external\safetyhook\src\mid_hook.x86_64-windows.asm" -o "%OUT%\mid_hook_asm.obj" || goto :error

echo === Compiling safetyhook ===
for %%f in (allocator easy inline_hook mid_hook os.windows utility vmt_hook) do (
  cl.exe %CXXFLAGS% %INC% /I"%SRC%\external\safetyhook\src" /c "%SRC%\external\safetyhook\src\%%f.cpp" /Fo"%OUT%\%%f.obj" || goto :error
)

echo === Compiling SDK function files ===
for %%f in (Basic CoreUObject_functions Engine_functions UMG_functions) do (
  cl.exe %CXXFLAGS% %INC% /c "%SRC%\src\SDK\%%f.cpp" /Fo"%OUT%\%%f.obj" || goto :error
)

echo === Compiling dllmain.cpp ===
cl.exe %CXXFLAGS% %INC% /c "%SRC%\src\dllmain.cpp" /Fo"%OUT%\dllmain.obj" || goto :error

echo === Linking ===
link.exe /nologo /DLL /OUT:"%OUT%\OctopathArabicRTL.asi" ^
  "%OUT%\*.obj" ^
  user32.lib kernel32.lib || goto :error

echo BUILD_SUCCESS
dir "%OUT%\OctopathArabicRTL.asi"
goto :eof

:error
echo BUILD_FAILED
exit /b 1
