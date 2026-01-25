@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul

set "DEFAULT_HOST=0.0.0.0"
set "DEFAULT_PORT=8000"
set "DEFAULT_WORKERS=4"
set "DEFAULT_ENV=dev"

set "HOST=%DEFAULT_HOST%"
set "PORT=%DEFAULT_PORT%"
set "WORKERS=%DEFAULT_WORKERS%"
set "ENV=%DEFAULT_ENV%"
set "COMMAND="

:parse_args
if "%~1"=="" goto :args_done
if /I "%~1"=="help" (set "COMMAND=help" & shift & goto :parse_args)
if /I "%~1"=="--help" (set "COMMAND=help" & shift & goto :parse_args)
if /I "%~1"=="dev" (if not defined COMMAND set "COMMAND=dev" & shift & goto :parse_args)
if /I "%~1"=="prod" (if not defined COMMAND set "COMMAND=prod" & shift & goto :parse_args)
if /I "%~1"=="uvicorn" (if not defined COMMAND set "COMMAND=uvicorn" & shift & goto :parse_args)
if /I "%~1"=="scheduler" (if not defined COMMAND set "COMMAND=scheduler" & shift & goto :parse_args)
if /I "%~1"=="migrate" (if not defined COMMAND set "COMMAND=migrate" & shift & goto :parse_args)
if /I "%~1"=="init" (if not defined COMMAND set "COMMAND=init" & shift & goto :parse_args)
if /I "%~1"=="install" (if not defined COMMAND set "COMMAND=install" & shift & goto :parse_args)
if /I "%~1"=="loaddata" (if not defined COMMAND set "COMMAND=loaddata" & shift & goto :parse_args)
if /I "%~1"=="shell" (if not defined COMMAND set "COMMAND=shell" & shift & goto :parse_args)
if /I "%~1"=="stop" (if not defined COMMAND set "COMMAND=stop" & shift & goto :parse_args)
if /I "%~1"=="status" (if not defined COMMAND set "COMMAND=status" & shift & goto :parse_args)
if /I "%~1"=="-h" (
  set "NEXT=%~2"
  if "!NEXT!"=="" (echo [ERROR] Missing value for -h & goto :show_help)
  if "!NEXT:~0,1!"=="-" (echo [ERROR] Missing value for -h & goto :show_help)
  set "HOST=!NEXT!" & shift & shift & goto :parse_args
)
if /I "%~1"=="--host" (
  set "NEXT=%~2"
  if "!NEXT!"=="" (echo [ERROR] Missing value for --host & goto :show_help)
  if "!NEXT:~0,1!"=="-" (echo [ERROR] Missing value for --host & goto :show_help)
  set "HOST=!NEXT!" & shift & shift & goto :parse_args
)
if /I "%~1"=="-p" (
  set "NEXT=%~2"
  if "!NEXT!"=="" (echo [ERROR] Missing value for -p & goto :show_help)
  if "!NEXT:~0,1!"=="-" (echo [ERROR] Missing value for -p & goto :show_help)
  set "PORT=!NEXT!" & shift & shift & goto :parse_args
)
if /I "%~1"=="--port" (
  set "NEXT=%~2"
  if "!NEXT!"=="" (echo [ERROR] Missing value for --port & goto :show_help)
  if "!NEXT:~0,1!"=="-" (echo [ERROR] Missing value for --port & goto :show_help)
  set "PORT=!NEXT!" & shift & shift & goto :parse_args
)
if /I "%~1"=="-w" (
  set "NEXT=%~2"
  if "!NEXT!"=="" (echo [ERROR] Missing value for -w & goto :show_help)
  if "!NEXT:~0,1!"=="-" (echo [ERROR] Missing value for -w & goto :show_help)
  set "WORKERS=!NEXT!" & shift & shift & goto :parse_args
)
if /I "%~1"=="--workers" (
  set "NEXT=%~2"
  if "!NEXT!"=="" (echo [ERROR] Missing value for --workers & goto :show_help)
  if "!NEXT:~0,1!"=="-" (echo [ERROR] Missing value for --workers & goto :show_help)
  set "WORKERS=!NEXT!" & shift & shift & goto :parse_args
)
if /I "%~1"=="-e" (
  set "NEXT=%~2"
  if "!NEXT!"=="" (echo [ERROR] Missing value for -e & goto :show_help)
  if "!NEXT:~0,1!"=="-" (echo [ERROR] Missing value for -e & goto :show_help)
  set "ENV=!NEXT!" & shift & shift & goto :parse_args
)
if /I "%~1"=="--env" (
  set "NEXT=%~2"
  if "!NEXT!"=="" (echo [ERROR] Missing value for --env & goto :show_help)
  if "!NEXT:~0,1!"=="-" (echo [ERROR] Missing value for --env & goto :show_help)
  set "ENV=!NEXT!" & shift & shift & goto :parse_args
)
if not defined COMMAND (set "COMMAND=%~1" & shift & goto :parse_args)
shift
goto :parse_args

:args_done
if not defined COMMAND set "COMMAND=help"
set "ZQ_ENV=%ENV%"

if /I "%COMMAND%"=="help" goto :show_help
if /I "%COMMAND%"=="--help" goto :show_help
if /I "%COMMAND%"=="dev" goto :cmd_dev
if /I "%COMMAND%"=="prod" goto :cmd_prod
if /I "%COMMAND%"=="uvicorn" goto :cmd_uvicorn
if /I "%COMMAND%"=="scheduler" goto :cmd_scheduler
if /I "%COMMAND%"=="migrate" goto :cmd_migrate
if /I "%COMMAND%"=="init" goto :cmd_init
if /I "%COMMAND%"=="install" goto :cmd_install
if /I "%COMMAND%"=="loaddata" goto :cmd_loaddata
if /I "%COMMAND%"=="shell" goto :cmd_shell
if /I "%COMMAND%"=="stop" goto :cmd_stop
if /I "%COMMAND%"=="status" goto :cmd_status

echo [ERROR] Unknown command: %COMMAND%
goto :show_help

:show_help
echo.
echo ==========================================
echo   ZQ Platform Backend Django Start Script
echo ==========================================
echo.
echo Usage: start.bat [command] [options]
echo.
echo Commands:
echo   dev           Start Django dev server (runserver)
echo   prod          Start production server (gunicorn + uvicorn worker)
echo   uvicorn       Start uvicorn ASGI server
echo   scheduler     Start scheduler
echo   migrate       Run migrations
echo   init          Init project (install + migrate + loaddata)
echo   install       Install python deps
echo   loaddata      Load initial data
echo   shell         Django shell
echo   stop          Stop background processes (best-effort)
echo   status        Show running status (best-effort)
echo   help          Show help
echo.
echo Options:
echo   -h, --host    Bind host (default: %DEFAULT_HOST%)
echo   -p, --port    Bind port (default: %DEFAULT_PORT%)
echo   -w, --workers Worker count (default: %DEFAULT_WORKERS%)
echo   -e, --env     Env dev^|uat^|prd (default: %DEFAULT_ENV%)
echo.
goto :done

:activate_venv
if exist "venv\Scripts\activate.bat" (
  call "venv\Scripts\activate.bat"
  exit /b 0
)
python -m venv venv
if errorlevel 1 exit /b 1
call "venv\Scripts\activate.bat"
exit /b 0

:install_dependencies
pip install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple -r requirements.txt
exit /b %ERRORLEVEL%

:check_dependencies
python -c "import django" >nul 2>nul
if errorlevel 1 (
  call :install_dependencies
  exit /b %ERRORLEVEL%
)
exit /b 0

:create_directories
if not exist "logs" mkdir "logs"
if not exist "media" mkdir "media"
if not exist "media\file_manager" mkdir "media\file_manager"
if not exist "static" mkdir "static"
if not exist "static\swagger-ui" mkdir "static\swagger-ui"
if not exist "templates" mkdir "templates"
if not exist "templates\ninja" mkdir "templates\ninja"
exit /b 0

:check_swagger_ui
set "SWAGGER_CSS=%SCRIPT_DIR%static\swagger-ui\swagger-ui.css"
set "SWAGGER_JS=%SCRIPT_DIR%static\swagger-ui\swagger-ui-bundle.js"
set "DOWNLOAD_SCRIPT=%SCRIPT_DIR%..\tools\download_swagger_ui.py"
if exist "%SWAGGER_CSS%" if exist "%SWAGGER_JS%" exit /b 0
if exist "%DOWNLOAD_SCRIPT%" (
  python "%DOWNLOAD_SCRIPT%" --target "%SCRIPT_DIR%static\swagger-ui"
  exit /b %ERRORLEVEL%
)
exit /b 0

:run_migrate
python manage.py makemigrations core scheduler
if errorlevel 1 exit /b 1
python manage.py migrate
exit /b %ERRORLEVEL%

:load_data
if exist "db_init.json" (
  python manage.py loaddata db_init.json
  exit /b %ERRORLEVEL%
)
exit /b 0

:ensure_ready
call :activate_venv
if errorlevel 1 exit /b 1
call :check_dependencies
if errorlevel 1 exit /b 1
call :create_directories
if errorlevel 1 exit /b 1
call :check_swagger_ui
exit /b 0

:cmd_dev
call :ensure_ready
if errorlevel 1 goto :fail
echo [INFO] URL: http://%HOST%:%PORT%
echo [INFO] ENV: %ENV%
python manage.py runserver %HOST%:%PORT%
goto :done

:cmd_uvicorn
call :ensure_ready
if errorlevel 1 goto :fail
echo [INFO] URL: http://%HOST%:%PORT%
echo [INFO] ENV: %ENV%
echo [INFO] WORKERS: %WORKERS%
uvicorn application.asgi:application --host %HOST% --port %PORT% --workers %WORKERS% --log-level info --access-log
goto :done

:cmd_prod
call :ensure_ready
if errorlevel 1 goto :fail
echo [INFO] URL: http://%HOST%:%PORT%
echo [INFO] ENV: %ENV%
echo [INFO] WORKERS: %WORKERS%
gunicorn application.asgi:application --bind %HOST%:%PORT% --workers %WORKERS% --worker-class uvicorn.workers.UvicornWorker --timeout 120 --keep-alive 5 --max-requests 1000 --max-requests-jitter 50 --access-logfile logs/access.log --error-logfile logs/error.log --capture-output --log-level info
goto :done

:cmd_scheduler
call :ensure_ready
if errorlevel 1 goto :fail
echo [INFO] ENV: %ENV%
python start_scheduler.py
goto :done

:cmd_migrate
call :ensure_ready
if errorlevel 1 goto :fail
call :run_migrate
if errorlevel 1 goto :fail
goto :done

:cmd_install
call :activate_venv
if errorlevel 1 goto :fail
call :install_dependencies
if errorlevel 1 goto :fail
goto :done

:cmd_loaddata
call :ensure_ready
if errorlevel 1 goto :fail
call :load_data
if errorlevel 1 goto :fail
goto :done

:cmd_shell
call :ensure_ready
if errorlevel 1 goto :fail
python manage.py shell
goto :done

:cmd_init
call :activate_venv
if errorlevel 1 goto :fail
call :install_dependencies
if errorlevel 1 goto :fail
call :create_directories
if errorlevel 1 goto :fail
call :check_swagger_ui
call :run_migrate
if errorlevel 1 goto :fail
call :load_data
if errorlevel 1 goto :fail
echo [INFO] Init done.
goto :done

:cmd_stop
powershell -NoProfile -Command ^
  "$targets=@('*manage.py runserver*','*start_scheduler.py*','*uvicorn*application.asgi*','*gunicorn*application.asgi*');" ^
  "$procs=Get-CimInstance Win32_Process ^| Where-Object { $null -ne $_.CommandLine };" ^
  "foreach($t in $targets){" ^
  "  $m=$procs ^| Where-Object { $_.CommandLine -like $t };" ^
  "  foreach($p in $m){ try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop } catch {} }" ^
  "}" ^
  "exit 0"
goto :done

:cmd_status
powershell -NoProfile -Command ^
  "$items=@(" ^
  "  @{Name='Gunicorn'; Pattern='*gunicorn*application.asgi*'}," ^
  "  @{Name='Uvicorn'; Pattern='*uvicorn*application.asgi*'}," ^
  "  @{Name='Scheduler'; Pattern='*start_scheduler.py*'}," ^
  "  @{Name='Runserver'; Pattern='*manage.py runserver*'}" ^
  ");" ^
  "$procs=Get-CimInstance Win32_Process ^| Where-Object { $null -ne $_.CommandLine };" ^
  "foreach($i in $items){" ^
  "  $m=$procs ^| Where-Object { $_.CommandLine -like $i.Pattern } ^| Select-Object -First 1;" ^
  "  if($m){" ^
  "    Write-Output ('[RUNNING] {0} PID={1}' -f $i.Name,$m.ProcessId);" ^
  "  } else {" ^
  "    Write-Output ('[STOPPED] {0}' -f $i.Name);" ^
  "  }" ^
  "}" ^
  "exit 0"
goto :done

:fail
echo [ERROR] Failed.
exit /b 1

:done
popd >nul
exit /b 0

