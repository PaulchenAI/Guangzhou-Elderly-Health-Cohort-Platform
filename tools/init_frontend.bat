@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "FRONTEND_DIR=%PROJECT_ROOT%\web"
set "APP_DIR=%FRONTEND_DIR%\apps\web-ele"
set "ENV_DEV_FILE=%APP_DIR%\.env.development"
set "ENV_PROD_FILE=%APP_DIR%\.env.production"

set "REQUIRED_NODE_VERSION=20.10.0"
set "REQUIRED_PNPM_VERSION=9.12.0"

set "VITE_APP_NAMESPACE=zq-platform"
set "VITE_PORT=5173"
set "VITE_BASE=/"
set "VITE_GLOB_API_URL=/basic-api"
set "VITE_NITRO_MOCK=false"
set "VITE_DEVTOOLS=true"
set "VITE_INJECT_APP_LOADING=true"
set "VITE_ROUTER_HISTORY=history"
set "PROD_API_URL=https://django-ninja.zq-platform.cn"

echo ========================================
echo Frontend initialization
echo ========================================

echo [1/5] Check Node.js...
where node >nul 2>nul
if errorlevel 1 (
  echo ERROR: Node.js not found
  echo Please install Node.js ^>= %REQUIRED_NODE_VERSION%
  exit /b 1
)
for /f %%V in ('node -p "process.versions.node"') do set "CURRENT_NODE_VERSION=%%V"
echo Current Node.js: %CURRENT_NODE_VERSION%
powershell -NoProfile -Command "if ([version]'%CURRENT_NODE_VERSION%' -ge [version]'%REQUIRED_NODE_VERSION%') { exit 0 } else { exit 1 }"
if errorlevel 1 (
  echo ERROR: Node.js version too low. Required ^>= %REQUIRED_NODE_VERSION%
  echo This project uses Vite 7 which requires Node.js ^>= %REQUIRED_NODE_VERSION% on Windows.
  echo Suggested fix:
  echo   - Install Node.js 20 LTS or newer, then reopen terminal and run this script again.
  where nvm >nul 2>nul
  if not errorlevel 1 (
    echo Detected nvm-windows. Example:
    echo   nvm install 20.11.1
    echo   nvm use 20.11.1
    echo   node -v
  )
  exit /b 1
)

echo [2/5] Check pnpm...
where pnpm >nul 2>nul
if errorlevel 1 (
  echo pnpm not found. Installing...
  where npm >nul 2>nul
  if errorlevel 1 (
    echo ERROR: npm not found, cannot install pnpm
    exit /b 1
  )
  npm install -g pnpm@latest
  if errorlevel 1 exit /b 1
) else (
  for /f %%V in ('pnpm -v') do set "CURRENT_PNPM_VERSION=%%V"
  echo Current pnpm: %CURRENT_PNPM_VERSION%
  powershell -NoProfile -Command "if ([version]'%CURRENT_PNPM_VERSION%' -ge [version]'%REQUIRED_PNPM_VERSION%') { exit 0 } else { exit 1 }"
  if errorlevel 1 (
    echo pnpm version too low. Upgrading...
    npm install -g pnpm@latest
    if errorlevel 1 exit /b 1
  )
)

echo [3/5] Install dependencies...
if not exist "%FRONTEND_DIR%\package.json" (
  echo ERROR: Frontend dir not found: %FRONTEND_DIR%
  exit /b 1
)
pushd "%FRONTEND_DIR%" >nul
if exist "node_modules" (
  if defined ZQ_NONINTERACTIVE (
    echo node_modules exists. Reusing.
  ) else if defined ZQ_AUTO (
    echo node_modules exists. Reusing.
  ) else (
    choice /M "node_modules exists. Delete and reinstall"
    if errorlevel 2 (
      echo Reusing existing node_modules
    ) else (
      echo Removing node_modules...
      rmdir /s /q "node_modules"
      pnpm install
      if errorlevel 1 (popd & exit /b 1)
    )
  )
) else (
  pnpm install
  if errorlevel 1 (popd & exit /b 1)
)
popd >nul

echo [4/5] Create env files...
if not exist "%APP_DIR%" (
  echo ERROR: App dir not found: %APP_DIR%
  exit /b 1
)

set "CREATE_DEV_ENV="
if exist "%ENV_DEV_FILE%" (
  if defined ZQ_NONINTERACTIVE (
    set "CREATE_DEV_ENV="
  ) else (
    choice /M ".env.development exists. Overwrite"
    if errorlevel 1 set "CREATE_DEV_ENV=true"
  )
) else (
  set "CREATE_DEV_ENV=true"
)

set "CREATE_PROD_ENV="
if exist "%ENV_PROD_FILE%" (
  if defined ZQ_NONINTERACTIVE (
    set "CREATE_PROD_ENV="
  ) else (
    choice /M ".env.production exists. Overwrite"
    if errorlevel 1 set "CREATE_PROD_ENV=true"
  )
) else (
  set "CREATE_PROD_ENV=true"
)

if "%CREATE_DEV_ENV%"=="true" (
  powershell -NoProfile -Command ^
    "$enc=New-Object System.Text.UTF8Encoding($true);" ^
    "$title=-join ([char]0x82B7,[char]0x9752,[char]0x5F00,[char]0x53D1,[char]0x5E73,[char]0x53F0);" ^
    "$lines=@(" ^
    "'# Development env',", ^
    "'VITE_APP_TITLE='+$title,", ^
    "'VITE_APP_NAMESPACE=%VITE_APP_NAMESPACE%',", ^
    "'VITE_PORT=%VITE_PORT%',", ^
    "'VITE_BASE=%VITE_BASE%',", ^
    "'VITE_GLOB_API_URL=%VITE_GLOB_API_URL%',", ^
    "'VITE_NITRO_MOCK=%VITE_NITRO_MOCK%',", ^
    "'VITE_DEVTOOLS=%VITE_DEVTOOLS%',", ^
    "'VITE_INJECT_APP_LOADING=%VITE_INJECT_APP_LOADING%',", ^
    "'VITE_ROUTER_HISTORY=%VITE_ROUTER_HISTORY%'" ^
    ");" ^
    "[System.IO.File]::WriteAllLines('%ENV_DEV_FILE%',$lines,$enc)"
)

if "%CREATE_PROD_ENV%"=="true" (
  powershell -NoProfile -Command ^
    "$enc=New-Object System.Text.UTF8Encoding($true);" ^
    "$title=-join ([char]0x82B7,[char]0x9752,[char]0x5F00,[char]0x53D1,[char]0x5E73,[char]0x53F0);" ^
    "$lines=@(" ^
    "'# Production env',", ^
    "'VITE_APP_TITLE='+$title,", ^
    "'VITE_APP_NAMESPACE=%VITE_APP_NAMESPACE%',", ^
    "'VITE_BASE=%VITE_BASE%',", ^
    "'VITE_GLOB_API_URL=%PROD_API_URL%',", ^
    "'VITE_COMPRESS=gzip',", ^
    "'VITE_PWA=false',", ^
    "'VITE_ROUTER_HISTORY=%VITE_ROUTER_HISTORY%',", ^
    "'VITE_INJECT_APP_LOADING=%VITE_INJECT_APP_LOADING%',", ^
    "'VITE_ARCHIVER=false'" ^
    ");" ^
    "[System.IO.File]::WriteAllLines('%ENV_PROD_FILE%',$lines,$enc)"
)

echo [5/5] Summary
echo   Frontend: %FRONTEND_DIR%
echo   App:      %APP_DIR%
echo   Port:     %VITE_PORT%
echo   API:      %VITE_GLOB_API_URL% (proxied to http://localhost:8000)

if defined ZQ_NONINTERACTIVE goto :done
if defined ZQ_AUTO goto :done
choice /M "Start dev server now"
if errorlevel 2 goto :done
pushd "%FRONTEND_DIR%" >nul
pnpm dev
popd >nul

:done
echo Done.
exit /b 0

