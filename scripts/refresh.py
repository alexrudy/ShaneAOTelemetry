#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
from telemetry.cli import parser
from telemetry.application import app
from telemetry.celery import is_available
from telemetry.tasks import refresh
from telemetry.models import Dataset
from astropy.utils.console import ProgressBar
from celery import group


def main():
    """Make various generated telemetry components."""
    opt = parser(None)
    
    with app.app_context():
        session = app.session
        query = opt.filter(session.query(Dataset))
        
        if not is_available():
            for dataset in ProgressBar(query.all()):
                dataset.update()
                session.add(dataset)
            session.commit()
        else:
            datasets = query.all()
            tasks = [refresh.si(dataset.id) for dataset in datasets]
            g = group(*tasks)
            result = g.delay()
            result.get()

if __name__ == '__main__':
    main()