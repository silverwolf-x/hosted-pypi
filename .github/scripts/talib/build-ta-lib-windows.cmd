@echo on

if "%TALIB_C_VER%"=="" (
  echo TALIB_C_VER is required
  exit /B 1
)

set CMAKE_GENERATOR=NMake Makefiles
set CMAKE_BUILD_TYPE=Release
set CMAKE_CONFIGURATION_TYPES=Release

curl -fsSL -o talib-c.zip https://github.com/TA-Lib/ta-lib/archive/refs/tags/v%TALIB_C_VER%.zip
if errorlevel 1 exit /B 1

tar -xf talib-c.zip
if errorlevel 1 exit /B 1

setlocal
cd ta-lib-%TALIB_C_VER%

if not exist include\ta-lib mkdir include\ta-lib
copy /Y include\*.h include\ta-lib\
if errorlevel 1 exit /B 1

if not exist _build md _build
cd _build

cmake.exe .. -G "%CMAKE_GENERATOR%" -DCMAKE_BUILD_TYPE=%CMAKE_BUILD_TYPE%
if errorlevel 1 exit /B 1

nmake.exe /nologo all
if errorlevel 1 exit /B 1

copy /Y /B ta-lib-static.lib ta-lib.lib
if errorlevel 1 exit /B 1

endlocal