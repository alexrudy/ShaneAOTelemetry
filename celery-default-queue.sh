#!/usr/bin/env bash
celery -A telemetry.celery worker -lINFO --concurrency=10 -n default.%h --autoreload