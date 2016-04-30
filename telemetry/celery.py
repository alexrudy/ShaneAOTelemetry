# -*- coding: utf-8 -*-
from __future__ import absolute_import
from .application import app
celery = app.celery
del app

def is_available():
    """Is celery available"""
    from celery.task.control import inspect
    try:
        insp = inspect()
        d = insp.stats()
    except IOError as e:
        return False
    except ImportError as e:
        print(e)
        return False
    else:
        return True