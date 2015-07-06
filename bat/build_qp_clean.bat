@echo off
:: build_qp_clean.bat
:: Version 1.0 2015-06-25
::
:: A script to delete all build_qpid and build_proton build/install folders.
::
:: Usage: build_qp_clean.bat
::
:: Show what will be deleted
SET ANY_WORK=
FOR /f "delims=" %%F IN ('DIR /B BUILD_20*')   DO SET ANY_WORK=1 && ECHO Will delete: %%F
FOR /f "delims=" %%F IN ('DIR /B INSTALL_20*') DO SET ANY_WORK=1 && ECHO Will delete: %%F

IF DEFINED ANY_WORK (ECHO Press Ctrl-C to abort && PAUSE)

FOR /f "delims=" %%F IN ('DIR /B BUILD_20*')   DO CALL :DelDir %%F
FOR /f "delims=" %%F IN ('DIR /B INSTALL_20*') DO CALL :DelDir %%F
goto :eof

REM
REM DelDir dirname
REM
:DelDir
echo DelDir: Deleting %1.
rmdir /s /q %1
echo DelDir: Checking if %1 still exists
if exist %1\nul (echo "%1 still exists. Type Ctrl-C to exit and fix %1" && pause && goto :eof)
goto :eof
