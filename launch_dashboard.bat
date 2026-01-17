@echo off
REM Urban Simulator Dashboard Launcher
REM ===================================
REM
REM Usage:
REM   launch_dashboard.bat              - Open HTML dashboard
REM   launch_dashboard.bat streamlit    - Launch Streamlit dashboard
REM   launch_dashboard.bat regenerate   - Rebuild HTML dashboard
REM   launch_dashboard.bat info         - Show dashboard information

setlocal enabledelayedexpansion

REM Get script directory
set "SCRIPT_DIR=%~dp0"

REM Check if argument provided
if "%1"=="" (
    echo.
    echo ======================================================================
    echo URBAN SIMULATOR CALIBRATION DASHBOARD
    echo ======================================================================
    echo.
    echo Launching HTML Dashboard...
    echo.
    
    REM Check if dashboard exists
    if exist "%SCRIPT_DIR%urban_simulator_dashboard.html" (
        echo [OK] Opening dashboard file...
        start "" "%SCRIPT_DIR%urban_simulator_dashboard.html"
    ) else (
        echo [*] Dashboard not found. Generating...
        cd /d "%SCRIPT_DIR%"
        python dashboard.py
        if exist "%SCRIPT_DIR%urban_simulator_dashboard.html" (
            start "" "%SCRIPT_DIR%urban_simulator_dashboard.html"
        )
    )
    
    goto end
)

if "%1"=="streamlit" (
    echo.
    echo ======================================================================
    echo URBAN SIMULATOR CALIBRATION DASHBOARD - STREAMLIT
    echo ======================================================================
    echo.
    echo Launching Streamlit Dashboard...
    echo Dashboard will open at: http://localhost:8501
    echo.
    
    cd /d "%SCRIPT_DIR%"
    python -m streamlit run streamlit_dashboard.py
    goto end
)

if "%1"=="regenerate" (
    echo.
    echo ======================================================================
    echo REGENERATING DASHBOARD
    echo ======================================================================
    echo.
    
    cd /d "%SCRIPT_DIR%"
    python dashboard.py
    goto end
)

if "%1"=="info" (
    echo.
    echo ======================================================================
    echo URBAN SIMULATOR DASHBOARD - INFORMATION
    echo ======================================================================
    echo.
    echo AVAILABLE DASHBOARDS:
    echo =====================
    echo 1. Static HTML Dashboard
    echo    - No dependencies required
    echo    - File: urban_simulator_dashboard.html
    echo    - Launch: launch_dashboard.bat
    echo.
    echo 2. Interactive Streamlit Dashboard
    echo    - Real-time filters and interactions
    echo    - Launch: launch_dashboard.bat streamlit
    echo    - Requires: pip install streamlit
    echo.
    echo QUICK START:
    echo ============
    echo For HTML dashboard:
    echo   launch_dashboard.bat
    echo.
    echo For Streamlit dashboard:
    echo   launch_dashboard.bat streamlit
    echo.
    echo To regenerate dashboard:
    echo   launch_dashboard.bat regenerate
    echo.
    echo FEATURES:
    echo =========
    echo - Rent calibration comparison
    echo - Real data analysis (51 neighborhoods^)
    echo - Demographics and displacement mechanics
    echo - Error analysis and validation
    echo - Module metrics (all 11 urban modules^)
    echo - Calibration timeline (8-phase program^)
    echo.
    echo DATA SOURCES:
    echo =============
    echo - real_rent_calibration_2024.csv
    echo - population_scaling_factors.csv
    echo - baseline_simulation_state.csv
    echo - zone_definitions_2024.csv
    echo - 300+ database records
    echo.
    echo REPOSITORY:
    echo ===========
    echo GitHub: https://github.com/sivanarayanchalla/holistic-urban-simulator
    echo Status: All 8 calibration phases completed (100%%^)
    echo.
    goto end
)

echo Unknown argument: %1
echo.
echo Usage:
echo   launch_dashboard.bat              - Open HTML dashboard
echo   launch_dashboard.bat streamlit    - Launch Streamlit dashboard
echo   launch_dashboard.bat regenerate   - Rebuild HTML dashboard
echo   launch_dashboard.bat info         - Show dashboard information
echo.

:end
endlocal
