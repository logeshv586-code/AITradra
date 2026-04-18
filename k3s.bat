@echo off
setlocal enabledelayedexpansion

:: AITradra k3s Flag Translator
:: Translates legacy -resolv-conf flag to modern --resolv-conf format

set "RAW_ARGS=%*"
set "FIXED_ARGS=%RAW_ARGS:-resolv-conf=--resolv-conf%"

:: Log the translation for debugging
echo [AITradra-Shim] Intercepted k3s call.
echo [AITradra-Shim] Original: k3s %RAW_ARGS%
echo [AITradra-Shim] Translated: k3s %FIXED_ARGS%
echo.

:: Execute the real k3s (assumes k3s.exe is in PATH)
k3s.exe %FIXED_ARGS%
