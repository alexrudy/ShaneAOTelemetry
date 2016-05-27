#!/usr/bin/env bash
if [ $# -gt 0 ]; then
    echo $#
    celery -A telemetry.celery multi stop default --pidfile=celery/run/%n.pid
else
    echo "restart"
    celery -A telemetry.celery multi restart default -linfo --pidfile=celery/run/%n.pid --autoreload --logfile=celery/log/%n.log
fi
