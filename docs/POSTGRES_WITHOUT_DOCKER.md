# PostgreSQL without Docker (Windows)

Use this path when **Docker Desktop cannot start** because virtualization is disabled in firmware, Hyper-V/WSL2 is unavailable, or IT policy blocks nested virtualization.

PAS production **requires PostgreSQL**. Docker Compose is optional — not required for controlled go-live.

Related: [PRODUCTION_GO_LIVE.md](PRODUCTION_GO_LIVE.md), `backend/.env.example`.

---

## When you see this Docker error

> Virtualization support not detected  
> Docker Desktop failed to start because virtualisation support wasn't detected.

**Typical root cause (check with `systeminfo`):**

```text
Hyper-V Requirements: ... Virtualization Enabled In Firmware: No
```

If firmware virtualization is **No**, Docker Desktop (WSL2 or Hyper-V backend) will not run until BIOS/UEFI is changed. Prefer **native PostgreSQL** below for go-live on that machine.

---

## Path A — Enable virtualization (optional; for Docker later)

Only needed if you want Docker Compose. Skip if you install native Postgres (Path B).

### 1. BIOS / UEFI (required when firmware says No)

1. Restart → enter BIOS/UEFI (HP often **Esc** then **F10**, or **F10** at splash).
2. Enable **Intel Virtualization Technology (VT-x)** / **SVM Mode** (AMD) / **Virtualization Technology**.
3. Save and exit; boot Windows.
4. Confirm: `systeminfo` → **Virtualization Enabled In Firmware: Yes**.

You may need an IT admin if the BIOS is password-locked.

### 2. Windows features (Windows 10 **Pro** / Enterprise)

Open an **elevated** PowerShell:

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
```

Or: *Settings → Apps → Optional features → More Windows features* → enable **Hyper-V**, **Virtual Machine Platform**, **Windows Subsystem for Linux**.

Reboot, then start Docker Desktop.

### 3. Windows 10 **Home**

Hyper-V is not available. Use **WSL2 + Virtual Machine Platform**:

```powershell
wsl --install
```

Or enable **Virtual Machine Platform** + **Windows Subsystem for Linux**, reboot, install a distro (`wsl --install -d Ubuntu`), then start Docker Desktop (WSL2 backend).

### 4. After BIOS + features

Docker can work once firmware virtualization is **Yes** and WSL2 or Hyper-V is enabled. Until then, use Path B.

---

## Path B — Native PostgreSQL on Windows (recommended when Docker fails)

### Install

**Option 1 — winget** (needs network + usually admin; EDB download may return 403 from some networks):

```powershell
winget search PostgreSQL.PostgreSQL
winget install --id PostgreSQL.PostgreSQL.17 -e --accept-package-agreements
```

**Option 2 — Official installer** (reliable):

1. Download Windows x64 installer from [PostgreSQL Windows downloads](https://www.postgresql.org/download/windows/) (EnterpriseDB).
2. Run the installer as Administrator.
3. Note the **superuser (`postgres`) password** and port (**5432**).
4. Optionally install **Command Line Tools** / Stack Builder components you need; pgAdmin is optional.

Add `bin` to PATH if the installer did not (example):

```powershell
$env:Path += ';C:\Program Files\PostgreSQL\17\bin'
```

Verify:

```powershell
psql --version
Get-Service -Name '*postgres*'
```

### Create database and app user

Match `backend/.env.example` (`DB_*`). Example (change the password):

```powershell
# Connect as superuser (prompts for postgres password)
& 'C:\Program Files\PostgreSQL\17\bin\psql.exe' -U postgres -h localhost -p 5432
```

In `psql`:

```sql
CREATE USER pas WITH PASSWORD 'change-me-strong';
CREATE DATABASE payroll OWNER pas;
GRANT ALL PRIVILEGES ON DATABASE payroll TO pas;
\c payroll
GRANT ALL ON SCHEMA public TO pas;
\q
```

Simpler go-live (use the built-in `postgres` role, as in `.env.example`):

```sql
CREATE DATABASE payroll OWNER postgres;
\q
```

### Configure `backend/.env`

Copy `backend/.env.example` → `backend/.env` (never commit `.env`):

```env
SECRET_KEY=change-me-to-a-long-random-value
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=payroll
DB_USER=postgres
DB_PASSWORD=your-postgres-password
DB_HOST=localhost
DB_PORT=5432

DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=change-me-strong-password
```

For local smoke only you may use `DEBUG=True` and development settings; production payroll needs production settings + Postgres.

### Migrate and admin (PowerShell)

```powershell
cd C:\Users\Prudhvi\PAS-Payroll-Automation-System\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements\production.txt
$env:DJANGO_SETTINGS_MODULE = 'config.settings.production'
python manage.py migrate
python manage.py check
python manage.py ensure_admin
# Or interactive: python manage.py createsuperuser
python manage.py collectstatic --noinput
python manage.py runserver 0.0.0.0:8000
# Production: gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

Adjust the repo path if your clone lives elsewhere.

### SQLite note

Leaving `DB_NAME` empty uses SQLite — fine for **non-production practice only**. Do **not** run live payroll on SQLite.

---

## Docker is not required for first live company

Controlled go-live needs:

1. Native or remote **PostgreSQL** with `DB_*` set  
2. Migrations + admin (`ensure_admin` / `createsuperuser`)  
3. Follow [PRODUCTION_GO_LIVE.md](PRODUCTION_GO_LIVE.md)

Use Docker only when virtualization works and you prefer Compose.
