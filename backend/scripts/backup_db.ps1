# Backup database (PostgreSQL or SQLite) - PowerShell
#
# Usage (from repo or any cwd):
#   .\backend\scripts\backup_db.ps1
#   .\backend\scripts\backup_db.ps1 -OutputDir "D:\pas-backups"
#
# Postgres: set DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT (or rely on defaults).
# SQLite: leave DB_NAME empty; backs up backend\db.sqlite3

param(
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
$BackendRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutputDir) {
    $OutputDir = Join-Path $BackendRoot "backups"
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$envFile = Join-Path $BackendRoot ".env"

function Get-EnvValue([string]$key) {
    if (Test-Path $envFile) {
        $line = Get-Content $envFile | Where-Object { $_ -match "^\s*$key\s*=" } | Select-Object -First 1
        if ($line) {
            return ($line -split "=", 2)[1].Trim().Trim('"').Trim("'")
        }
    }
    return [Environment]::GetEnvironmentVariable($key)
}

$dbName = Get-EnvValue "DB_NAME"
if ($dbName) {
    $dbUser = Get-EnvValue "DB_USER"; if (-not $dbUser) { $dbUser = "postgres" }
    $dbHost = Get-EnvValue "DB_HOST"; if (-not $dbHost) { $dbHost = "localhost" }
    $dbPort = Get-EnvValue "DB_PORT"; if (-not $dbPort) { $dbPort = "5432" }
    $dbPassword = Get-EnvValue "DB_PASSWORD"
    $outFile = Join-Path $OutputDir "pas_${dbName}_$stamp.dump"
    if ($dbPassword) {
        $env:PGPASSWORD = $dbPassword
    }
    Write-Host "Backing up PostgreSQL database '$dbName' to $outFile"
    & pg_dump -Fc -h $dbHost -p $dbPort -U $dbUser -d $dbName -f $outFile
    if ($LASTEXITCODE -ne 0) { throw "pg_dump failed with exit code $LASTEXITCODE" }
} else {
    $sqlite = Join-Path $BackendRoot "db.sqlite3"
    if (-not (Test-Path $sqlite)) { throw "No DB_NAME set and $sqlite not found" }
    $outFile = Join-Path $OutputDir "pas_sqlite_$stamp.sqlite3"
    Write-Host "Backing up SQLite to $outFile (dev only - not for production payroll)"
    Copy-Item $sqlite $outFile
}

$item = Get-Item $outFile
if ($item.Length -le 0) { throw "Backup file is empty: $outFile" }
Write-Host ("OK: {0} ({1} bytes)" -f $item.FullName, $item.Length)
Write-Host "Next: verify restore on staging per docs/BACKUP_AND_RESTORE.md"
