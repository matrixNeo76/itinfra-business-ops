@echo off
setlocal
set "BASEDIR=%~dp0"

if "%~1"=="" goto help
if "%~1"=="help" goto help
if "%~1"=="-h" goto help
if "%~1"=="--help" goto help

python "%BASEDIR%scripts\it_ops.py" %*
exit /b %ERRORLEVEL%

:help
echo.
echo ==============================================================================
echo  itinfra-business-ops CLI (it-ops)
echo  Governance Operativa, Commerciale, Contratti SLA, MPS e Arredo Ufficio
echo ==============================================================================
echo.
echo UTILIZZO:
echo   it-ops ^<comando^> [slug] [opzioni]
echo.
echo COMANDI DISPONIBILI:
echo   init ^<slug^> [--client "Nome"]   Inizializza una nuova anagrafica cliente
echo   status ^<slug^>                   Visualizza la scheda esecutiva 360 del cliente
echo   check ^<slug^>                    Cross-check apparati con l'As-Built in itinfra
echo   contract ^<slug^> [status]        Gestione contratti SLA, monte ore e alert
echo   report ^<slug^> [balance]         Gestione rapportini di assistenza e ore
echo   billing ^<slug^> [summary]        Batch di fatturazione mensile e scadenziario
echo   mps ^<slug^> [calculate]          Telelettura stampanti, costo copia e toner
echo   furniture ^<slug^> [status]       Stato avanzamento commessa arredo e collaudo
echo   quote ^<slug^> [calculate]        Calcolo preventivi multiprodotto con ricarichi
echo   validate ^<path^>                 Validazione deterministica a fronte degli schemi
echo.
exit /b 0
