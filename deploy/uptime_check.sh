#!/usr/bin/env bash
# DeepSentinel Uptime & Health Monitor
# Queries /api/health and alerts if the endpoint fails or returns non-200.
#
# Usage:
#   ./deploy/uptime_check.sh [URL]
# Example:
#   HEALTH_URL=https://beta.deepsentinel.ai/api/health ./deploy/uptime_check.sh
# Cron (every 5 minutes):
#   */5 * * * * /app/deploy/uptime_check.sh https://beta.deepsentinel.ai/api/health >> /var/log/deepsentinel_uptime.log 2>&1

set -euo pipefail

URL="${1:-${HEALTH_URL:-http://localhost:8080/api/health}}"
ALERT_WEBHOOK_URL="${ALERT_WEBHOOK_URL:-}"
MAX_TIMEOUT=10

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Run curl and measure response time and HTTP status code
RESPONSE=$(curl -s -w "\n%{http_code}\n%{time_total}" --max-time "${MAX_TIMEOUT}" "${URL}" || echo -e "FAILED\n000\n0.0")

BODY=$(echo "${RESPONSE}" | sed '$d' | sed '$d')
HTTP_CODE=$(echo "${RESPONSE}" | tail -n 2 | head -n 1)
TIME_TOTAL=$(echo "${RESPONSE}" | tail -n 1)

if [ "${HTTP_CODE}" = "200" ] && echo "${BODY}" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'; then
    echo "[${TIMESTAMP}] [HEALTHY] 200 OK | Target: ${URL} | Latency: ${TIME_TOTAL}s"
    exit 0
else
    ERROR_MSG="[${TIMESTAMP}] [DOWN ALERT] DeepSentinel health check FAILED! Target: ${URL} | HTTP: ${HTTP_CODE} | Latency: ${TIME_TOTAL}s | Response: ${BODY}"
    echo "${ERROR_MSG}" >&2

    # Send alert to syslog
    if command -v logger >/dev/null 2>&1; then
        logger -p user.emerg -t deepsentinel-monitor "${ERROR_MSG}"
    fi

    # Webhook alert if configured
    if [ -n "${ALERT_WEBHOOK_URL}" ]; then
        curl -s -X POST -H "Content-Type: application/json" \
             -d "{\"text\": \"${ERROR_MSG}\"}" "${ALERT_WEBHOOK_URL}" || true
    fi

    exit 1
fi
