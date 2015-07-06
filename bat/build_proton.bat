@echo off
::
:: Licensed to the Apache Software Foundation (ASF) under one
:: or more contributor license agreements.  See the NOTICE file
:: distributed with this work for additional information
:: regarding copyright ownership.  The ASF licenses this file
:: to you under the Apache License, Version 2.0 (the
:: "License"); you may not use this file except in compliance
:: with the License.  You may obtain a copy of the License at
::
::   http://www.apache.org/licenses/LICENSE-2.0
::
:: Unless required by applicable law or agreed to in writing,
:: software distributed under the License is distributed on an
:: "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
:: KIND, either express or implied.  See the License for the
:: specific language governing permissions and limitations
:: under the License.
::

::
:: build_proton.bat
:: Version 1.4 2015-05-21
::
:: Usage: build_proton.bat INSTALL_ROOT_PATH [2008|2010|2012|2013 x64|x86 [any         [any]]]
::                         %1                 %2                  %3       %4           %5
::                                                                         keep build  keep install
:: A script to cmake/make/install proton on windows.
::
:: This script expects to execute from the root of a proton checkout,
:: the directory that holds proton-c and proton-j.
::
:: It produces an installed directory that qpid can share to get 1.0 support.
::
:: Cmake and the compiles will be in the current directory:
::      .\build_2008_x86
::      .\build_2010_x86
::      .\build_2008_x64
::      .\build_2010_x64
::
:: Installs are steered to four directories under INSTALL_ROOT_PATH in %1.
::      %1%\install_2008_x86
::      %1%\install_2010_x86
::      %1%\install_2008_x64
::      %1%\install_2010_x64
::
::   The install directories are suitable to be consumed in a
::   qpid\cpp build:
::      cmake ... -DCMAKE_INSTALL_PREFIX=<INSTALL_ROOT_PATH>\install_2010_x86 ...
::   where the qpid build does not know nor care if proton is installed.
::   If proton is present then it is included, otherwise not.
::
:: Note: This script blindly tries to compile proton whether the requested 
:: compiler is installed or not. Don't call build_proton with args that
:: your computer can't satisfy.
::
:: Hacky external CR_UNATTENDED inhibits pause before each build.

:: Check that CD is a proton checkout
IF NOT exist .\proton-c (echo This script must execute from a proton checkout root && pause && goto :eof)
IF NOT exist .\proton-j (echo This script must execute from a proton checkout root && pause && goto :eof)

:: Check that the INSTALL_ROOT_PATH is specified
IF "%1"=="" (echo You must specify an INSTALL_ROOT_PATH && GOTO :Usage)

:: Check for help
IF "%1"=="help"  GOTO :Usage
IF "%1"=="/help" GOTO :Usage
IF "%1"=="?"     GOTO :Usage
IF "%1"=="/?"    GOTO :Usage
IF "%1"=="-?"    GOTO :Usage
set xx=%1
IF "%xx:~0,2%"=="-h"    GOTO :Usage
IF "%xx:~0,3%"=="--h"   GOTO :Usage

SET INSTALL_ROOT=%~f1%
::set INSTALL_ROOT=d:\users\crolke\git\rh-qpid-proton\install_022
:: Forgive a trailing slash
IF "%INSTALL_ROOT:~-1%"=="\" SET INSTALL_ROOT=%INSTALL_ROOT:~0,-1%
ECHO Installing to %INSTALL_ROOT%

:: See if build of specific compile/arch is specified
SET cli_compiler=%2
SET cli_arch=%3

:: Get directory flush inhibitor switches
SET keep_build=%4
SET keep_install=%5
IF DEFINED keep_build   (SET   keep_build=true) else (SET   keep_build=false)
IF DEFINED keep_install (SET keep_install=true) else (SET keep_install=false)

:: build either once from the command line setting or N times from the list below
SET cli_build=false
IF DEFINED cli_compiler IF DEFINED cli_arch (SET cli_build=true)
IF "%cli_build%"=="true" (
    call :build_proton %cli_compiler% %cli_arch% %INSTALL_ROOT% "%keep_build%" "%keep_install%"
) ELSE (
    call :build_proton 2008 x86  %INSTALL_ROOT% "%keep_build%" "%keep_install%"
    call :build_proton 2010 x86  %INSTALL_ROOT% "%keep_build%" "%keep_install%"
    call :build_proton 2012 x86  %INSTALL_ROOT% "%keep_build%" "%keep_install%"
    call :build_proton 2013 x86  %INSTALL_ROOT% "%keep_build%" "%keep_install%"
    call :build_proton 2008 x64  %INSTALL_ROOT% "%keep_build%" "%keep_install%"
    call :build_proton 2010 x64  %INSTALL_ROOT% "%keep_build%" "%keep_install%"
    call :build_proton 2012 x64  %INSTALL_ROOT% "%keep_build%" "%keep_install%"
    call :build_proton 2013 x64  %INSTALL_ROOT% "%keep_build%" "%keep_install%"
)
goto :eof

::
:: build a proton
::  %1 selects architecture x86 or x64
::  %2 selects studio 2008 or 2010 or 2012 or 2013
::  %3 is fully qualified install root path with no trailing slash
::  %4 true|false to keep build directory
::  %5 true|false to keep install directory
:build_proton

:: push the env
setlocal

set vsname=%1
set arch=%2
set INSTALL_ROOT_PATH=%3
set keep_build=%4
set keep_install=%5

set   build_dir=build_%vsname%_%arch%
set install_dir=%INSTALL_ROOT_PATH%\install_%vsname%_%arch%

REM VS2008 or VS2010 or VS2012 or VS2013, x86 or x64
if "%vsname%"=="2008" (
    if "%arch%" == "x86" (
        call "%VS90COMNTOOLS%..\..\VC\vcvarsall.bat" x86
        if %errorlevel% neq 0 exit /b %errorlevel%
        set cmakegen="Visual Studio 9 2008"
        set proton_arch=Win32
    ) else (
        call "%VS90COMNTOOLS%..\..\VC\vcvarsall.bat" amd64
        if %errorlevel% neq 0 exit /b %errorlevel%
        set cmakegen="Visual Studio 9 2008 Win64"
        set proton_arch=x64
    )
)
if "%vsname%"=="2010" (
    if "%arch%" == "x86" (
        call "%VS100COMNTOOLS%..\..\VC\vcvarsall.bat" x86
        if %errorlevel% neq 0 exit /b %errorlevel%
        set cmakegen="Visual Studio 10"
        set proton_arch=Win32
    ) else (
        call "%VS100COMNTOOLS%..\..\VC\vcvarsall.bat" amd64
        if %errorlevel% neq 0 exit /b %errorlevel%
        set cmakegen="Visual Studio 10 Win64"
        set proton_arch=x64
    )
)
if "%vsname%"=="2012" (
    if "%arch%" == "x86" (
        call "%VS110COMNTOOLS%..\..\VC\vcvarsall.bat" x86
        if %errorlevel% neq 0 exit /b %errorlevel%
        set cmakegen="Visual Studio 11"
        set proton_arch=Win32
    ) else (
        call "%VS110COMNTOOLS%..\..\VC\vcvarsall.bat" amd64
        if %errorlevel% neq 0 exit /b %errorlevel%
        set cmakegen="Visual Studio 11 Win64"
        set proton_arch=x64
    )
)
if "%vsname%"=="2013" (
    if "%arch%" == "x86" (
        call "%VS120COMNTOOLS%..\..\VC\vcvarsall.bat" x86
        if %errorlevel% neq 0 exit /b %errorlevel%
        set cmakegen="Visual Studio 12"
        set proton_arch=Win32
    ) else (
        call "%VS120COMNTOOLS%..\..\VC\vcvarsall.bat" amd64
        if %errorlevel% neq 0 exit /b %errorlevel%
        set cmakegen="Visual Studio 12 Win64"
        set proton_arch=x64
    )
)
if "%proton_arch%"=="" (
	echo Arch not recognized : %arch%
	goto :eof
)

@echo off
echo.
echo ===================================================================
echo Ready to build.
echo Using visual studio : %vsname%
echo Architecture        : %arch%
echo Build directory     : %build_dir%
echo Install directory   : %install_dir%
echo Keep build dir      : %keep_build%
echo Keep install dir    : %keep_install%
echo .
IF NOT DEFINED CR_UNATTENDED (echo Press Enter to continue, Ctrl-C to abort && pause)
@echo on

:: fresh build/install areas
if   %keep_build%=="false" call :MakeNewDir   %build_dir%
if %keep_install%=="false" call :MakeNewDir %install_dir%

:: descend into build area
pushd %build_dir%

:: run cmake
cmake -G %cmakegen% -DCMAKE_INSTALL_PREFIX=%install_dir% -DGEN_JAVA=No -DBUILD_JAVA=No ..

:: build/install proton
devenv proton.sln /build "Debug|%proton_arch%"          /project INSTALL
if %errorlevel% neq 0 (echo FAIL FAIL FAIL: Studio failure building DEBUG %build_dir%)

devenv proton.sln /build "RelWithDebInfo|%proton_arch%" /project INSTALL
if %errorlevel% neq 0 (echo FAIL FAIL FAIL: Studio failure building RELWITHDEBINFO %build_dir%)

:: ascend from build area
popd

:: restore path and environment
endlocal

:: done
goto :eof

REM
REM MakeNewDir dirname
REM
:MakeNewDir
echo MakeNewDir: Start recreating %1. Delete %1
rmdir /s /q %1
echo MakeNewDir: Checking if %1 still exists
if exist %1\nul (echo "%1 still exists. Type Ctrl-C to exit and fix %1" && pause && goto :eof)
echo MakeNewDir: Create %1
mkdir       %1
echo MakeNewDIr: Done  recreating %1
goto :eof

REM
REM Usage
REM
:Usage
echo Usage: build_proton.bat INSTALL_ROOT_PATH [2008,2010,2012,2013 x64,x86 [any         [any]]]
echo                         arg1               arg2                arg3     arg4         arg5
echo                                                                         keep build  keep install
echo     arg1 INSTALL_ROOT_PATH [required] may be any absolute or relative path including '.' .
echo     arg2 CLI_COMPILER      [optional] may be 2008, 2010, 2012, or 2013. If absent the all are compiled.
echo     arg3 CLI_ARCH                     may be x86 or x64. If absent then all are compied.
echo     arg4 KEEP_BUILD        [optional] any text. If present then build directory is used and not flushed.
echo     arg5 KEEP_INSTALL      [optional] any text. If present then install directory is used and not flushed.
echo.     
echo     Build and Install directories for {2010, x86} will 'build_2010_x86' and 'install_2010_x86'.
echo     Other {compiler, arch} combinations follow the same pattern.
echo.     
echo     Define environment variable CR_UNATTENDED to skip pausing between build steps.
goto :eof
