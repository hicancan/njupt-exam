@echo off
cd /d "%~dp0.."

if not exist node_modules (
    echo [INFO] node_modules not found. Installing dependencies...
    call npm install
)

echo Starting Local Server for njupt-exam...
echo Serving project root from: %CD%
echo Please wait, opening browser...

start http://localhost:5173
call npm run dev
pause
