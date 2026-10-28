#!/usr/bin/env bash
# DeepSentinel Production Backup & Storage Monitoring Script
# Runs nightly via cron or systemd timer:
#   0 2 * * * /app/deploy/backup.sh >> /var/log/deepsentinel_backup.log 2>&1
#
# Requirements:
# 1. Keeps nightly pg_dump for 7 days (deleting older backups)
# 2. Alerts when media storage disk usage passes 80%

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/deepsentinel}"
RETENTION_DAYS=7
DISK_ALERT_THRESHOLD=80
MEDIA_DIR="${MEDIA_DIR:-./storage}"
POSTGRES_USER="${POSTGRES_USER:-deepfake}"
POSTGRES_DB="${POSTGRES_DB:-deepfake}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-deepfake}"
ALERT_WEBHOOK_URL="${ALERT_WEBHOOK_URL:-}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/deepsentinel_${TIMESTAMP}.sql.gz"

echo "=========================================================="
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting DeepSentinel Nightly Backup"
echo "=========================================================="

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# 1. Perform database backup
echo "[+] Creating PostgreSQL dump: ${BACKUP_FILE}"
if docker compose ps db --status running -q >/dev/null 2>&1; then
    docker compose exec -T db pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "${BACKUP_FILE}"
elif command -v pg_dump >/dev/null 2>&1 && [ -n "${DATABASE_URL:-}" ]; then
    pg_dump "${DATABASE_URL}" | gzip > "${BACKUP_FILE}"
else
    echo "[-] Error: Database container is not running and pg_dump not found!" >&2
    exit 1
fi

# Verify backup size
BACKUP_SIZE=$(stat -c%s "${BACKUP_FILE}" 2>/dev/null || stat -f%z "${BACKUP_FILE}" 2>/dev/null || wc -c < "${BACKUP_FILE}")
if [ "${BACKUP_SIZE}" -lt 100 ]; then
    echo "[-] Error: Backup file is suspiciously small (${BACKUP_SIZE} bytes). Dump may have failed!" >&2
    exit 1
fi
echo "[✓] Database backup completed (${BACKUP_SIZE} bytes)"

# 2. Enforce 7-day retention policy (prune backups older than 7 days)
echo "[+] Enforcing 7-day backup retention in ${BACKUP_DIR}..."
PRUNED_COUNT=$(find "${BACKUP_DIR}" -type f -name "deepsentinel_*.sql.gz" -mtime +${RETENTION_DAYS} | wc -l)
find "${BACKUP_DIR}" -type f -name "deepsentinel_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
echo "[✓] Pruned ${PRUNED_COUNT} backup(s) older than ${RETENTION_DAYS} days."

# 3. Check media disk usage
echo "[+] Checking media disk usage on ${MEDIA_DIR}..."
if [ -d "${MEDIA_DIR}" ]; then
    DISK_USAGE=$(df -P "${MEDIA_DIR}" | awk 'NR==2 {print $5}' | tr -d '%')
    echo "[i] Current media disk usage: ${DISK_USAGE}% (Threshold: ${DISK_ALERT_THRESHOLD}%)"

    if [ "${DISK_USAGE}" -ge "${DISK_ALERT_THRESHOLD}" ]; then
        ALERT_MSG="[CRITICAL ALERT] DeepSentinel media disk usage has reached ${DISK_USAGE}% (threshold is ${DISK_ALERT_THRESHOLD}%) on $(hostname)!"
        echo "[-] ${ALERT_MSG}" >&2

        # Send alert to syslog / systemd journal
        if command -v logger >/dev/null 2>&1; then
            logger -p user.crit -t deepsentinel "${ALERT_MSG}"
        fi

        # Send alert via webhook if configured
        if [ -n "${ALERT_WEBHOOK_URL}" ]; then
            curl -s -X POST -H "Content-Type: application/json" \
                 -d "{\"text\": \"${ALERT_MSG}\"}" "${ALERT_WEBHOOK_URL}" || true
        fi
    else
        echo "[✓] Disk usage is within healthy limits (${DISK_USAGE}% < ${DISK_ALERT_THRESHOLD}%)."
    fi
else
    echo "[!] Warning: Media directory ${MEDIA_DIR} not found. Skipping disk usage check."
fi

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Backup and health verification completed successfully."
