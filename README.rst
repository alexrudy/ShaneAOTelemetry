Working with the telemetry suite
--------------------------------

Startup
=======

Launch the celery queues::
    ./celery-default-queue.sh

ShaneAO
=======

Download new data::
    ./manage.py shaneao download

Ingest new data::
    ./manage.py shaneao new /Volumes/.../path/to/files/

Concatenate into sequeces::
    ./manage.py shaneao concatenate