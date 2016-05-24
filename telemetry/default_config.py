CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_IMPORTS = ['telemetry.tasks',
    'telemetry.views.timeseries',
    'telemetry.ext.fourieranalysis.tasks']
CELERY_RESULT_BACKEND = "rpc://"
CELERY_DISABLE_RATE_LIMITS = True
CELERY_ROUTES = {'telemetry.views.timeseries.make_movie': {'queue': 'movies'}}
CELERYD_MAX_TASKS_PER_CHILD = 20

TELEMETRY_ENTRYPOINTS = ['fourieranalysis = telemetry.ext.fourieranalysis:setup', 'shaneao = telemetry.ext.shaneao:setup']
SQLALCHEMY_ECHO = False