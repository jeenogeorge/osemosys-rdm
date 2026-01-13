@echo off
REM Script to build PDF documentation using rinohtype
REM Usage: build_pdf.bat

echo ========================================
echo Building OSeMOSYS-RDM PDF Documentation
echo ========================================
echo.

REM Check if in correct directory
if not exist "conf.py" (
    echo Error: conf.py not found. Please run this script from the docs directory.
    exit /b 1
)

REM Create build directory if it doesn't exist
if not exist "_build\rinoh" mkdir "_build\rinoh"

echo Step 1: Installing/updating rinohtype...
pip install -q rinohtype
echo.

echo Step 2: Building PDF with Sphinx + rinohtype...
sphinx-build -b rinoh . _build/rinoh
echo.

if exist "_build\rinoh\osemosys-rdm.pdf" (
    echo ========================================
    echo SUCCESS! PDF generated successfully
    echo ========================================
    echo.
    echo PDF location: _build\rinoh\osemosys-rdm.pdf
    echo.
    start _build\rinoh
) else (
    echo ========================================
    echo ERROR: PDF generation failed
    echo ========================================
    echo Check the output above for errors.
)

pause