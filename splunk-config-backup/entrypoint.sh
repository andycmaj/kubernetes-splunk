#!/bin/sh

set +e

if [[ ${BACKUP_TIMEZONE} ]]; then
  # See http://wiki.alpinelinux.org/wiki/Setting_the_timezone
  cp /usr/share/zoneinfo/${BACKUP_TIMEZONE} /etc/localtime
  echo "${BACKUP_TIMEZONE}" >  /etc/timezone
fi

# Every day at 2am (UTC)
BACKUP_CRON_SCHEDULE=${BACKUP_CRON_SCHEDULE:-"00 09 * * *"}

echo "${BACKUP_CRON_SCHEDULE} /usr/local/bin/backup.sh >> /var/log/splunk-config-backup.log 2>&1" > /etc/crontabs/root

# Starting cron
crond -f -d 0
