#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
from telemetry.cli import parser, resultset_progress
from telemetry.application import app
from telemetry.celery import is_available
from telemetry.tasks import refresh
from telemetry.models import Dataset
from celery import group



def main():
    """Make various generated telemetry components."""
    with app.app_context():
        query = app.session.query(Dataset)
        print("Refreshing {:d} datasets.".format(query.count()))
        g = group(refresh.si(dataset.id) for dataset in query.all())
        if not is_available():
            g().get()
        else:
            resultset_progress(g.delay())

if __name__ == '__main__':
    main()