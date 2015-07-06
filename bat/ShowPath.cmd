@echo off
REM 
REM Show the current process's path in human readable format
REM
REM crolke 20100409
REM
REM Any arg causes "quiet" mode
REM
IF "%1"=="" (
echo.
echo current PATH environment
echo.
CALL :ShowThePath
echo.
) ELSE (
CALL :ShowThePath
)
GOTO :EOF

:ShowThePath
echo %path% | tr ';' '\n'
GOTO :EOF