#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
import collections
from telemetry.cli import parser, resultset_progress
from telemetry.models import TelemetryKind, Dataset
from telemetry.tasks import rgenerate
from telemetry.application import app
from celery import group

def setup(parser):
    """Set up the argument parser"""
    parser.add_argument("kind", type=str, help="Data kind.")
    parser.add_argument("-r", "--recursive", action="store_true", help="Should recursively generate dependents.")
    
def get_kind(session, h5path):
    """Get a telemetry kind from an h5path."""
    kind = session.query(TelemetryKind).filter(TelemetryKind.h5path == h5path).one_or_none()
    if kind is None:
        session.add(TelemetryKind(name=h5path, h5path=h5path))
        session.commit()
        kind = session.query(TelemetryKind).filter(TelemetryKind.h5path == h5path).one()
    return kind

def main():
    """Make various generated telemetry components."""
    opt = parser(setup)
    
    with app.app_context():
        session = app.session
        kind = get_kind(session, opt.kind)
        print(kind)
        if not hasattr(kind, 'generate'):
            opt.error("{0} does not appear to have a .generate() method.".format(type(kind).__name__))
        prerequisties = kind.rprerequisites
    
        done = session.query(Dataset.id).join(Dataset.kinds).filter(TelemetryKind.h5path == prerequisties[-1].h5path)
        if opt.recursive:
            print(prerequisties[0].h5path)
            query = session.query(Dataset).join(Dataset.kinds).filter(TelemetryKind.h5path == prerequisties[0].h5path)
            for p in prerequisties:
                query = p.filter(query)
        else:
            print(prerequisties[-2].h5path)
            query = session.query(Dataset).join(Dataset.kinds).filter(TelemetryKind.h5path == prerequisties[-2].h5path)
            query = kind.filter(query)
    
        if not opt.force:
            query = query.filter(Dataset.id.notin_(done))
    
        if opt.date:
            query.filter(Dataset.id.in_(opt.query))
            print(opt.date)
        
    
        print("Generating {0} for {1} datasets.".format(kind.name, query.count()))
        print("{0:d} datasets already have {1}".format(done.count(), kind.name))
        print("Prerequisites:")
        for i, prereq in enumerate(kind.rprerequisites):
            print("{:d}) {:d} {:s}".format(i, prereq.id, prereq.h5path))
        g = group(rgenerate(dataset, kind) for dataset in query.all())
        resultset_progress(g.delay())

if __name__ == '__main__':
    main()