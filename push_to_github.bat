@echo off
REM Push to GitHub - Interactive Script
REM This script will guide you through pushing to GitHub

echo ===============================================
echo Holistic Urban Simulator - GitHub Push Script
echo ===============================================
echo.
echo This script will help you push to GitHub.
echo Make sure you've created a repo at: https://github.com/new
echo.

set /p USERNAME="Enter your GitHub username: "
set /p REPO_NAME="Enter your repository name (press Enter for 'holistic-urban-simulator'): "

if "%REPO_NAME%"=="" (
    set REPO_NAME=holistic-urban-simulator
)

echo.
echo ===============================================
echo Settings:
echo - Username: %USERNAME%
echo - Repository: %REPO_NAME%
echo ===============================================
echo.

cd /d "c:\Users\sivan\OneDrive\Documents\Rag projects\urban Simulator\holistic_urban_simulator"

echo Adding remote origin...
git remote add origin https://github.com/%USERNAME%/%REPO_NAME%.git

echo Renaming branch to main...
git branch -M main

echo.
echo About to push to: https://github.com/%USERNAME%/%REPO_NAME%
echo You may be prompted for your GitHub credentials.
echo If using 2FA, use a Personal Access Token as password.
echo.

pause

echo Pushing to GitHub...
git push -u origin main

echo.
echo ===============================================
echo Push complete!
echo View your repository at: https://github.com/%USERNAME%/%REPO_NAME%
echo ===============================================
pause
