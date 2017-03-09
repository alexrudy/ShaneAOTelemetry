#!/usr/bin/env bash
if [ $# -gt 0 ]; then
    echo "stopping"
    celery -A telemetry.celery multi stop 2 --pidfile=celery/run/%n.pid
else
    echo "restarting"
    celery -A telemetry.celery multi restart 2 -linfo --pidfile=celery/run/%n.pid --logfile=celery/log/%n.log -c 2
fi
