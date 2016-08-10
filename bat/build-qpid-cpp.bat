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
:: build-qpid-cpp.bat
:: Version 1.5 2015-07-09
:: Version 1.6 2016-03-08 Add VS2015
:: Version 1.7 2016-08-02 From build_qpid now build-qpid-cpp new repo
::
:: Usage: build-qpid-cpp.bat [2008|2010|2012|2013|2015 x64|x86 [any        ]]
::                            %1                       %2       %3
::                                                              keep build
:: A script to cmake/make/install qpid on windows.
::
:: Note that users must edit this script to locate BOOST.
::
:: This script expects to execute from the root of a qpid-cpp checkout
::
:: It assumes an installed directory that may be prepopulated with proton for
:: AMQP 1.0 support.
::
:: Cmake and the compiles will be in subfolder of the current directory:
::      .\build_2008_x86
::      .\build_2010_x86
::      .\build_2008_x64
::      .\build_2010_x64
::
:: Installs are steered to subfolders
::      .\install_2008_x86
::      .\install_2010_x86
::      .\install_2008_x64
::      .\install_2010_x64

:: Check that CD is a qpid checkout
IF NOT exist .\bindings (echo This script must execute from a qpid-cpp checkout root with cpp folder in it && pause && goto :eof)
IF NOT exist .\rubygen  (echo This script must execute from a qpid-cpp checkout root with cpp folder in it && pause && goto :eof)

:: Check for help
IF "%1"==""      GOTO :Usage
IF "%1"=="help"  GOTO :Usage
IF "%1"=="/help" GOTO :Usage
IF "%1"=="?"     GOTO :Usage
IF "%1"=="/?"    GOTO :Usage
IF "%1"=="-?"    GOTO :Usage
set xx=%1
IF "%xx:~0,2%"=="-h"    GOTO :Usage
IF "%xx:~0,3%"=="--h"   GOTO :Usage

:: See if build of specific compile/arch is specified
SET cli_compiler=%1
SET cli_arch=%2

:: Get directory flush inhibitor switches
:: Note this procedure always keeps the install directory or else it will wipe
:: out Proton goodies. If you want to wipe the install do it yourself.
SET keep_build=%3
IF DEFINED keep_build   (SET   keep_build=true) else (SET   keep_build=false)

:: build either once from the command line setting or N times from the list below
SET cli_build=false
IF DEFINED cli_compiler IF DEFINED cli_arch (SET cli_build=true)
IF "%cli_build%"=="true" (
    call :build_qpid %cli_compiler% %cli_arch% "%keep_build%"
) ELSE (
    call :build_qpid 2008 x86 "%keep_build%"
    call :build_qpid 2010 x86 "%keep_build%"
    call :build_qpid 2012 x86 "%keep_build%"
    call :build_qpid 2013 x86 "%keep_build%"
    call :build_qpid 2015 x86 "%keep_build%"
    call :build_qpid 2008 x64 "%keep_build%"
    call :build_qpid 2010 x64 "%keep_build%"
    call :build_qpid 2012 x64 "%keep_build%"
    call :build_qpid 2013 x64 "%keep_build%"
    call :build_qpid 2015 x64 "%keep_build%"
)
goto :eof

:: build a qpid
::  %1 selects architecture x86 or x64
::  %2 selects studio: 2008, 2010, 2012, 2013, or 2015
::  %3 true|false to keep build directory
:build_qpid

setlocal

set vsname=%1
set arch=%2
set keep_build=%3

set   build_dir=build_%vsname%_%arch%
set install_dir=.\install_%vsname%_%arch%

:: Select a boost root
if "%vsname%"=="2008" (
    if "%arch%" == "x86" (
        SET MY_BOOST_ROOT=c:\boost-win-1.47-32bit-vs2008
    ) else (
        SET MY_BOOST_ROOT=c:\boost-win-1.47-64bit-vs2008
    )
)
if "%vsname%"=="2010" (
    if "%arch%" == "x86" (
        SET MY_BOOST_ROOT=c:\boost-win-1.47-32bit-vs2010
    ) else (
        SET MY_BOOST_ROOT=c:\boost-win-1.47-64bit-vs2010
    )
)
if "%vsname%"=="2012" (
    if "%arch%" == "x86" (
        SET MY_BOOST_ROOT=c:\boost-win-1.53-32bit-vs2012
    ) else (
        SET MY_BOOST_ROOT=c:\boost-win-1.53-64bit-vs2012
    )
)
if "%vsname%"=="2013" (
    if "%arch%" == "x86" (
        SET MY_BOOST_ROOT=c:\boost
    ) else (
        echo "ERROR: Install a boost for VS2013 x64, please"
        exit /b 1
    )
)
if "%vsname%"=="2015" (
    if "%arch%" == "x86" (
        SET MY_BOOST_ROOT=c:\boost
    ) else (
        echo "ERROR: Install a boost for VS2013 x64, please"
        exit /b 1
    )
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
echo .
IF NOT DEFINED CR_UNATTENDED (echo Press Enter to continue, Ctrl-C to abort && pause)
@echo on

:: fresh build/install areas
if   %keep_build%=="false" call :MakeNewDir %build_dir%
:: Note don't recreate install dir as that kills the intalled proton

:: use built-in procedure to run cmake and churn out supporting scripts
powershell  -ExecutionPolicy unrestricted -File B:\configure-windows.ps1 %vsname%_%arch% %MY_BOOST_ROOT%
cd %build_dir%
call make-install

:: Copy the qpid-proton dlls from install dir into build\src\Debug

copy ..\install_%vsname%_%arch%\bin\qpid-proton*.dll .\src\Debug\
copy ..\install_%vsname%_%arch%\bin\boost*.dll       .\src\Debug\
goto :eof

REM
REM MakeNewDir dirname
REM
:MakeNewDir
echo MakeNewDir: Start recreating %1. Delete %1
rmdir /s /q %1
timeout /t 1 /nobreak > nul
echo MakeNewDir: Checking if %1 still exists
if exist %1\nul (echo "%1 still exists. Type ^C to exit and fix %1" && pause && goto :eof)
echo MakeNewDir: Create %1
mkdir       %1
echo MakeNewDIr: Done  recreating %1
goto :eof

REM
REM Usage
REM
:Usage
echo Usage: build-qpid-cpp.bat [2008,2010,2012,2013 x64,x86 [any]]
echo                            arg1                arg2     arg3
echo                                                         keep build
echo     arg1 CLI_COMPILER      [optional] may be 2008, 2010, 2012, or 2013. If absent the all are compiled.
echo     arg2 CLI_ARCH                     may be x86 or x64. If absent then all are compied.
echo     arg3 KEEP_BUILD        [optional] any text. If present then build directory is used and not flushed.
echo.     
echo     Build and Install directories for {2010, x86} will './build_2010_x86' and './install_2010_x86'.
echo     Other {compiler, arch} combinations follow the same pattern.
echo.     
echo     Define environment variable CR_UNATTENDED to skip pausing between build steps.
goto :eof
