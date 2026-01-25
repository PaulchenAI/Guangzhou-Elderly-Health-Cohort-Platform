@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_DIR=%PROJECT_ROOT%\backend-django"
set "ENV_FILE=%BACKEND_DIR%\.env"
set "DEV_ENV_FILE=%BACKEND_DIR%\env\dev_env.py"

set "DB_USER=fuadmin"
set "DB_PASSWORD=fuadmin"
set "DB_NAME=fuadmin2"
set "DB_HOST=127.0.0.1"
set "DB_PORT=3306"
set "REDIS_HOST=127.0.0.1"
set "REDIS_PASSWORD="
set "REDIS_PORT=6379"
set "REDIS_DB=2"

echo ========================================
echo Backend initialization
echo ========================================

echo [1/7] Check Python 3.11...
set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 (
  py -3.11 --version >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=py -3.11"
)
if "%PYTHON_CMD%"=="" (
  where python >nul 2>nul
  if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.11
    exit /b 1
  )
  set "CURRENT_PY_VERSION="
  for /f "tokens=1,2" %%A in ('python -V 2^>^&1') do (
    if /i "%%A"=="Python" set "CURRENT_PY_VERSION=%%B"
  )
  if "%CURRENT_PY_VERSION%"=="" (
    echo WARN: Failed to read Python version. Skipping version check.
    set "PYTHON_CMD=python"
    goto :py_ok
  )
  powershell -NoProfile -Command "if ([version]'%CURRENT_PY_VERSION%' -ge [version]'3.11.0') { exit 0 } else { exit 1 }"
  if errorlevel 1 (
    echo ERROR: Python version too low. Required ^>= 3.11.0
    exit /b 1
  )
  set "PYTHON_CMD=python"
)
:py_ok

echo [2/7] Create venv...
if not exist "%BACKEND_DIR%" (
  echo ERROR: Backend dir not found: %BACKEND_DIR%
  exit /b 1
)
pushd "%BACKEND_DIR%" >nul
if exist "venv" (
  if defined ZQ_NONINTERACTIVE (
    echo venv exists. Reusing.
  ) else (
    choice /M "venv exists. Delete and recreate"
    if errorlevel 2 (
      echo Reusing existing venv
    ) else (
      rmdir /s /q "venv"
      %PYTHON_CMD% -m venv venv
      if errorlevel 1 (popd & exit /b 1)
    )
  )
) else (
  %PYTHON_CMD% -m venv venv
  if errorlevel 1 (popd & exit /b 1)
)
popd >nul

echo [3/7] Create .env...
set "CREATE_ENV="
if exist "%ENV_FILE%" (
  if defined ZQ_NONINTERACTIVE (
    set "CREATE_ENV="
  ) else (
    choice /M ".env exists. Overwrite"
    if errorlevel 1 set "CREATE_ENV=true"
  )
) else (
  set "CREATE_ENV=true"
)
if "%CREATE_ENV%"=="true" (
  for /f "delims=" %%A in ('powershell -NoProfile -Command "$b=New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); -join ($b ^| ForEach-Object { $_.ToString('x2') })"') do set "JWT_ACCESS_SECRET_KEY=%%A"
  for /f "delims=" %%A in ('powershell -NoProfile -Command "$b=New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); -join ($b ^| ForEach-Object { $_.ToString('x2') })"') do set "JWT_REFRESH_SECRET_KEY=%%A"
  (
    echo DEV_DB_USER=%DB_USER%
    echo DEV_DB_PASSWORD=%DB_PASSWORD%
    echo JWT_ACCESS_SECRET_KEY=!JWT_ACCESS_SECRET_KEY!
    echo JWT_REFRESH_SECRET_KEY=!JWT_REFRESH_SECRET_KEY!
  )> "%ENV_FILE%"
)

echo [4/7] Update dev_env.py...
if not exist "%DEV_ENV_FILE%" (
  echo ERROR: File not found: %DEV_ENV_FILE%
  exit /b 1
)
copy /y "%DEV_ENV_FILE%" "%DEV_ENV_FILE%.bak" >nul
powershell -NoProfile -Command "$p='%DEV_ENV_FILE%'; $t=Get-Content -Raw -Encoding UTF8 $p; $t=[regex]::Replace($t,'(?m)^\s*DATABASE_NAME\s*=.*$','DATABASE_NAME = ''%DB_NAME%'''); $t=[regex]::Replace($t,'(?m)^\s*REDIS_PASSWORD\s*=.*$','REDIS_PASSWORD = ''%REDIS_PASSWORD%'''); $t=[regex]::Replace($t,'(?m)^\s*REDIS_HOST\s*=.*$','REDIS_HOST = ''%REDIS_HOST%'''); $t=[regex]::Replace($t,'(?m)^\s*REDIS_PORT\s*=\s*\d+','REDIS_PORT = %REDIS_PORT%'); $t=[regex]::Replace($t,'(?m)^\s*REDIS_DB\s*=.*$','REDIS_DB = ''%REDIS_DB%'''); Set-Content -Encoding UTF8 -NoNewline -Path $p -Value $t"
if errorlevel 1 exit /b 1

echo [5/7] MySQL init (optional)...
where mysql >nul 2>nul
if errorlevel 1 (
  echo mysql client not found. Skipped.
) else (
  set "SQL_FILE=%TEMP%\zq_init_mysql_%RANDOM%_%RANDOM%.sql"
  (
    echo CREATE DATABASE IF NOT EXISTS `%DB_NAME%` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    echo DROP USER IF EXISTS '%DB_USER%'@'localhost';
    echo DROP USER IF EXISTS '%DB_USER%'@'%%';
    echo DROP USER IF EXISTS '%DB_USER%'@'127.0.0.1';
    echo CREATE USER '%DB_USER%'@'localhost' IDENTIFIED WITH mysql_native_password BY '%DB_PASSWORD%';
    echo CREATE USER '%DB_USER%'@'%%' IDENTIFIED WITH mysql_native_password BY '%DB_PASSWORD%';
    echo CREATE USER '%DB_USER%'@'127.0.0.1' IDENTIFIED WITH mysql_native_password BY '%DB_PASSWORD%';
    echo GRANT ALL PRIVILEGES ON `%DB_NAME%`.* TO '%DB_USER%'@'localhost';
    echo GRANT ALL PRIVILEGES ON `%DB_NAME%`.* TO '%DB_USER%'@'%%';
    echo GRANT ALL PRIVILEGES ON `%DB_NAME%`.* TO '%DB_USER%'@'127.0.0.1';
    echo FLUSH PRIVILEGES;
  )> "!SQL_FILE!"
  if not defined MYSQL_ROOT_USER set "MYSQL_ROOT_USER=root"
  if defined ZQ_NONINTERACTIVE (
    if defined MYSQL_ROOT_PASSWORD (
      mysql -u "!MYSQL_ROOT_USER!" -p!MYSQL_ROOT_PASSWORD! -h "%DB_HOST%" -P %DB_PORT% < "!SQL_FILE!"
    ) else (
      echo INFO: MYSQL_ROOT_PASSWORD not set. Skipping MySQL init in non-interactive mode.
      set "MYSQL_EXIT=0"
      del /q "!SQL_FILE!" >nul 2>nul
      goto :mysql_done
    )
  ) else (
    set /p "MYSQL_ROOT_USER=MySQL admin user (default root): "
    if "!MYSQL_ROOT_USER!"=="" set "MYSQL_ROOT_USER=root"
    mysql -u "!MYSQL_ROOT_USER!" -p -h "%DB_HOST%" -P %DB_PORT% < "!SQL_FILE!"
  )
  set "MYSQL_EXIT=!ERRORLEVEL!"
  del /q "!SQL_FILE!" >nul 2>nul
  if not "!MYSQL_EXIT!"=="0" exit /b !MYSQL_EXIT!
)
:mysql_done

echo [6/7] Redis check (optional)...
where redis-cli >nul 2>nul
if errorlevel 1 (
  echo redis-cli not found. Skipped.
) else (
  redis-cli ping
)

echo [7/7] Optional: pip install / migrate / runserver...
if defined ZQ_AUTO goto :auto_steps
if defined ZQ_NONINTERACTIVE goto :done
choice /M "Install Python dependencies"
if errorlevel 2 goto :done
pushd "%BACKEND_DIR%" >nul
call "venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 (popd & exit /b 1)
pip install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple -r requirements.txt
if errorlevel 1 (popd & exit /b 1)
popd >nul

choice /M "Run migrations and init data"
if errorlevel 2 goto :done
pushd "%BACKEND_DIR%" >nul
call "venv\Scripts\activate.bat"
python manage.py makemigrations core scheduler
if errorlevel 1 (popd & exit /b 1)
python manage.py migrate
if errorlevel 1 (popd & exit /b 1)
if exist "db_init.json" python manage.py loaddata db_init.json
if errorlevel 1 (popd & exit /b 1)
choice /M "Start Django dev server"
if errorlevel 2 (popd & goto :done)
python manage.py runserver 0.0.0.0:8000
popd >nul

:auto_steps
pushd "%BACKEND_DIR%" >nul
call "venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 (popd & exit /b 1)
pip install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple -r requirements.txt
if errorlevel 1 (popd & exit /b 1)
python manage.py makemigrations core scheduler
if errorlevel 1 (popd & exit /b 1)
python manage.py migrate
if errorlevel 1 (popd & exit /b 1)
if exist "db_init.json" python manage.py loaddata db_init.json
if errorlevel 1 (popd & exit /b 1)
if defined ZQ_RUNSERVER (
  python manage.py runserver 0.0.0.0:8000
)
:auto_done
popd >nul

:done
echo Done.
exit /b 0

