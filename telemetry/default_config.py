CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_IMPORTS = ['telemetry.tasks', 'telemetry.ext.fourieranalysis.tasks']
CELERY_RESULT_BACKEND = "rpc://"

TELEMETRY_ENTRYPOINTS = ['fourieranalysis = telemetry.ext.fourieranalysis:setup', 'shaneao = telemetry.ext.shaneao:setup']
SQLALCHEMY_ECHO = False