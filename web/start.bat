@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul

set "REQUIRED_NODE_VERSION=22.1.0"
set "PORTABLE_NODE_VERSION=22.1.0"
set "DEFAULT_APP=ele"
set "DEFAULT_ENV=dev"
set "DEFAULT_PORT=5173"

set "COMMAND=%~1"
if "%COMMAND%"=="" set "COMMAND=dev"
shift

set "APP=%DEFAULT_APP%"
set "ENV=%DEFAULT_ENV%"
set "PORT=%DEFAULT_PORT%"
set "NO_INSTALL="

:parse_args
if "%~1"=="" goto :args_done
if /I "%~1"=="-a" (set "APP=%~2" & shift & shift & goto :parse_args)
if /I "%~1"=="--app" (set "APP=%~2" & shift & shift & goto :parse_args)
if /I "%~1"=="-e" (set "ENV=%~2" & shift & shift & goto :parse_args)
if /I "%~1"=="--env" (set "ENV=%~2" & shift & shift & goto :parse_args)
if /I "%~1"=="-p" (set "PORT=%~2" & shift & shift & goto :parse_args)
if /I "%~1"=="--port" (set "PORT=%~2" & shift & shift & goto :parse_args)
if /I "%~1"=="--no-install" (set "NO_INSTALL=1" & shift & goto :parse_args)
shift
goto :parse_args

:args_done

if /I "%COMMAND%"=="help" goto :show_help
if /I "%COMMAND%"=="--help" goto :show_help
if /I "%COMMAND%"=="-h" goto :show_help

call :ensure_node
if errorlevel 1 goto :fail

call :ensure_pnpm
if errorlevel 1 goto :fail

if not defined NO_INSTALL (
  call :ensure_install
  if errorlevel 1 goto :fail
)

call :resolve_target
if errorlevel 1 goto :fail

if /I "%COMMAND%"=="dev" goto :cmd_dev
if /I "%COMMAND%"=="preview" goto :cmd_preview
if /I "%COMMAND%"=="build" goto :cmd_build

echo ERROR: Unknown command: %COMMAND%
goto :show_help

:show_help
echo.
echo ==========================================
echo   ZQ Platform Frontend Start Script
echo ==========================================
echo.
echo Usage:
echo   start.bat [dev^|build^|preview] [options]
echo.
echo Options:
echo   -a, --app    ele^|antd^|naive^|docs^|play   (default: %DEFAULT_APP%)
echo   -e, --env    dev^|uat^|prd                  (default: %DEFAULT_ENV%)
echo   -p, --port   dev server port               (default: %DEFAULT_PORT%)
echo   --no-install skip pnpm install
echo.
echo Examples:
echo   start.bat dev -a ele -e dev -p 5173
echo   start.bat dev -a ele -e uat
echo   start.bat build -a ele -e prd
echo   start.bat preview -a ele
echo.
popd >nul
exit /b 0

:ensure_node
set "PORTABLE_NODE_DIR=%SCRIPT_DIR%\.node\node-v%PORTABLE_NODE_VERSION%-win-x64"
set "PORTABLE_NODE_EXE=%PORTABLE_NODE_DIR%\node.exe"
if exist "%PORTABLE_NODE_EXE%" (
  call :use_portable_node
  exit /b !ERRORLEVEL!
)
where node >nul 2>nul
if errorlevel 1 (
  echo ERROR: Node.js not found. Required ^>= %REQUIRED_NODE_VERSION%
  call :try_portable_node
  exit /b !ERRORLEVEL!
)
for /f %%V in ('node -p "process.versions.node"') do set "CURRENT_NODE_VERSION=%%V"
powershell -NoProfile -Command "if ([version]'%CURRENT_NODE_VERSION%' -ge [version]'%REQUIRED_NODE_VERSION%') { exit 0 } else { exit 1 }"
if not errorlevel 1 exit /b 0

echo ERROR: Node.js version too low. Current: %CURRENT_NODE_VERSION%  Required: ^>= %REQUIRED_NODE_VERSION%
call :try_portable_node
exit /b !ERRORLEVEL!

:try_portable_node
set "PORTABLE_NODE_DIR=%SCRIPT_DIR%\.node\node-v%PORTABLE_NODE_VERSION%-win-x64"
set "PORTABLE_NODE_EXE=%PORTABLE_NODE_DIR%\node.exe"
if exist "%PORTABLE_NODE_EXE%" goto :use_portable_node

echo [INFO] Installing portable Node.js v%PORTABLE_NODE_VERSION% under: %SCRIPT_DIR%\.node
if not exist "%SCRIPT_DIR%\.node" mkdir "%SCRIPT_DIR%\.node" >nul 2>nul
set "NODE_ZIP=%TEMP%\node-v%PORTABLE_NODE_VERSION%-win-x64.zip"
powershell -NoProfile -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$u='https://nodejs.org/dist/v%PORTABLE_NODE_VERSION%/node-v%PORTABLE_NODE_VERSION%-win-x64.zip';" ^
  "Write-Output ('Downloading '+$u);" ^
  "Invoke-WebRequest -Uri $u -OutFile '%NODE_ZIP%';" ^
  "Expand-Archive -Force -Path '%NODE_ZIP%' -DestinationPath '%SCRIPT_DIR%\.node';"
if errorlevel 1 (
  echo ERROR: Failed to download/extract portable Node.js.
  echo Please install Node.js ^>= %REQUIRED_NODE_VERSION% and rerun. Suggested: Node 20 LTS or newer.
  exit /b 1
)
if not exist "%PORTABLE_NODE_EXE%" (
  echo ERROR: Portable Node.js extracted but node.exe not found: %PORTABLE_NODE_EXE%
  exit /b 1
)

:use_portable_node
set "PATH=%PORTABLE_NODE_DIR%;%PATH%"
for /f %%V in ('node -p "process.versions.node"') do set "CURRENT_NODE_VERSION=%%V"
powershell -NoProfile -Command "if ([version]'%CURRENT_NODE_VERSION%' -ge [version]'%REQUIRED_NODE_VERSION%') { exit 0 } else { exit 1 }"
if errorlevel 1 (
  echo ERROR: Portable Node.js still not compatible. Current: %CURRENT_NODE_VERSION%
  exit /b 1
)
exit /b 0

:ensure_pnpm
where pnpm >nul 2>nul
if not errorlevel 1 exit /b 0
where npm >nul 2>nul
if errorlevel 1 (
  echo ERROR: pnpm not found and npm not found. Cannot proceed.
  exit /b 1
)
npm install -g pnpm@latest
exit /b %ERRORLEVEL%

:ensure_install
pnpm install
exit /b %ERRORLEVEL%

:resolve_target
set "TARGET_PKG="
if /I "%APP%"=="ele" set "TARGET_PKG=@vben/web-ele"
if /I "%APP%"=="antd" set "TARGET_PKG=@vben/web-antd"
if /I "%APP%"=="naive" set "TARGET_PKG=@vben/web-naive"
if /I "%APP%"=="docs" set "TARGET_PKG=@vben/docs"
if /I "%APP%"=="play" set "TARGET_PKG=@vben/playground"
if "%TARGET_PKG%"=="" (
  echo ERROR: Unknown app: %APP%
  exit /b 1
)

set "MODE=development"
if /I "%ENV%"=="dev" set "MODE=development"
if /I "%ENV%"=="uat" set "MODE=uat"
if /I "%ENV%"=="prd" set "MODE=production"
exit /b 0

:cmd_dev
set "PORT_ARG=--port"
echo [INFO] App: %TARGET_PKG%
echo [INFO] Mode: %MODE%
echo [INFO] Port: %PORT%
if /I "%MODE%"=="development" (
  pnpm -F %TARGET_PKG% run dev -- --port %PORT%
) else (
  pnpm -F %TARGET_PKG% exec vite -- --mode %MODE% --port %PORT%
)
popd >nul
exit /b 0

:cmd_build
echo [INFO] App: %TARGET_PKG%
echo [INFO] Mode: %MODE%
if /I "%MODE%"=="production" (
  pnpm -F %TARGET_PKG% run build
) else (
  pnpm -F %TARGET_PKG% exec vite -- build --mode %MODE%
)
popd >nul
exit /b 0

:cmd_preview
echo [INFO] App: %TARGET_PKG%
pnpm -F %TARGET_PKG% run preview
popd >nul
exit /b 0

:fail
popd >nul
exit /b 1
