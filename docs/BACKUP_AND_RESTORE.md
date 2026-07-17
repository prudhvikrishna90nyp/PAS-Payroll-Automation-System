# Backup and Restore (PAS)

PAS stores authoritative payroll data in the configured Django database (PostgreSQL in production). Media files (logos, proof uploads) live under `MEDIA_ROOT` (default `backend/media/`).

---

## What to back up

| Asset | Location | Notes |
|-------|----------|--------|
| Database | PostgreSQL (prod) or `db.sqlite3` (dev only) | Required |
| Media | `backend/media/` | Logos, investment proofs, uploads |
| `.env` / secrets | Secure secret store — **not** in git | Required for restore |
| Static collect | Regenerable via `collectstatic` | Optional |

---

## PostgreSQL backup

```bash
# Logical dump (recommended)
pg_dump -Fc -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f pas_$(date +%Y%m%d_%H%M%S).dump

# Plain SQL (portable)
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f pas_backup.sql
```

Schedule daily dumps (cron / Windows Task Scheduler) and retain at least 30 days off-host.

### Restore

```bash
# Custom format
pg_restore --clean --if-exists -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" pas_YYYYMMDD.dump

# Plain SQL
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f pas_backup.sql
```

After restore:

```bash
cd backend
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py migrate   # should be no-op if dump is current
python manage.py check
```

Restore `media/` from the matching archive next to the dump.

---

## Docker Compose

```bash
docker compose exec -T db pg_dump -U postgres pas > pas_backup.sql
# restore into a stopped/empty database carefully; prefer staging first
```

---

## SQLite (development only)

```bash
copy backend\db.sqlite3 backend\backups\db_YYYYMMDD.sqlite3
```

Do not use SQLite for production payroll.

---

## Verification checklist

- [ ] Backup job succeeded and file size &gt; 0
- [ ] Staging restore completed within target RTO
- [ ] Superuser can log in; latest locked payroll run visible
- [ ] Sample payslip / compliance export matches pre-backup snapshot
- [ ] Media logos and proof files load

---

## Notes

- Locked payroll runs are immutable in-app; backups remain the recovery path for catastrophic loss.
- Keep dump encryption and access control aligned with payroll confidentiality requirements.
