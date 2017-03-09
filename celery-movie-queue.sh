#!/usr/bin/env bash
celery -A telemetry.celery worker -lINFO --concurrency=1 -n movies.%h -Q movies