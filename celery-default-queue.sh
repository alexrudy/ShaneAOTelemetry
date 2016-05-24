#!/usr/bin/env bash
celery -A telemetry.celery worker -lINFO --concurrency=8 -n default.%h --autoreload