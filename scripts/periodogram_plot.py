#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
import os
from telemetry.cli import parser, resultset_progress
from telemetry.application import app
from telemetry.models import Telemetry, TelemetryKind, Dataset
from telemetry.fourieranalysis.tasks import periodoram_plot
from celery import group

import numpy as np

def setup(parser):
    """Set up the argument parser"""
    parser.add_argument("kind", type=str, help="Data kind to periodogram.")

def main():
    """Make various generated telemetry components."""
    opt = parser(setup)
    with app.app_context():
        session = app.session
        path = "periodogram/{0}".format(opt.kind)
        query = session.query(Dataset).join(Telemetry).join(Telemetry.kind).filter(TelemetryKind.h5path == path)
        if opt.date:
            query = query.filter(Dataset.id.in_(opt.query))
        g = group(periodoram_plot.si(dataset.id, opt.kind) for dataset in query.all())
        # next(iter(g)).delay().get()
        resultset_progress(g.delay())

if __name__ == '__main__':
    main()