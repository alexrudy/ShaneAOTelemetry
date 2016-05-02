#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
from telemetry.cli import parser, resultset_progress
from telemetry.application import app
from telemetry.models import TelemetryKind, Telemetry, Dataset
from telemetry.ext.fourieranalysis.models import *
from telemetry.ext.fourieranalysis.tasks import transferfunction
from celery import group

def setup(parser):
    """Set up the argument parser"""
    parser.add_argument("kind", type=str, help="Data kind to periodogram.")

def get_kind(session, h5path):
    """Get a telemetry kind from an h5path."""
    kind = session.query(TelemetryKind).filter(TelemetryKind.h5path == h5path).one_or_none()
    if kind is None:
        session.add(TelemetryKind(name=h5path, h5path=h5path))
        session.commit()
        kind = session.query(TelemetryKind).filter(TelemetryKind.h5path == h5path).one()
    return kind

def main():
    """Make transfer functions components."""
    opt = parser(setup)
    
    with app.app_context():
        name = "transferfunction/{0}".format(opt.kind)
        kind = get_kind(app.session, name)
    
        print(kind)
        if not hasattr(kind, 'generate'):
            opt.error("{0} does not appear to have a .generate() method.".format(type(kind).__name__))
    
        e_query = app.session.query(Dataset.id).join(Telemetry).join(TelemetryKind).filter(TelemetryKind.h5path == opt.kind)
        t_query = app.session.query(Dataset.id).join(Telemetry).join(TelemetryKind).filter(TelemetryKind.h5path == name)
        query = app.session.query(Dataset).filter(Dataset.id.in_(e_query)).join(Dataset.pairs)
    
        if opt.date is not None:
            e_query = opt.filter(e_query)
            t_query = opt.filter(t_query)
            query = opt.filter(query)
    
        print("{0:d} potential target datasets.".format(query.count()))
    
        if not opt.force:
            query = query.filter(Dataset.id.notin_(t_query))
    
        print("Generating {0} for {1} datasets.".format(kind.name, query.count()))
        print("{0:d} datasets already have {1}".format(t_query.count(), kind.name))
        
        g = group(transferfunction.si(dataset.id, opt.kind) for dataset in query.all())
        resultset_progress(g.delay())

if __name__ == '__main__':
    main()