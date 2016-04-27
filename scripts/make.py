#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
from telemetry.cli import parser
from telemetry.models import TelemetryKind, Dataset, Telemetry

def setup(parser):
    """Set up the argument parser"""
    parser.add_argument("kind", type=str, help="Data kind.")

def main():
    """Make various generated telemetry components."""
    opt = parser(setup)
    
    session = opt.session
    kind = session.query(TelemetryKind).filter(TelemetryKind.h5path == opt.kind).one_or_none()
    if kind is None:
        session.add(TelemetryKind(name=opt.kind, h5path=opt.kind))
        session.commit()
        kind = session.query(TelemetryKind).filter(TelemetryKind.h5path == opt.kind).one()
    
    if not hasattr(kind, 'generate'):
        opt.error("{0} does not appear to have a .generate() method.".format(type(kind).__name__))
    
    e_query = session.query(Dataset.id).join(Telemetry).join(TelemetryKind).filter(TelemetryKind.h5path == opt.kind)
    e_query = e_query.filter(Dataset.id.in_(opt.query))
    
    query = session.query(Dataset).filter(Dataset.id.in_(opt.query))
    if not opt.force:
        query = query.filter(~Dataset.id.in_(e_query))
    
    print("Generating {0} for {1} datasets.".format(kind.name, query.count()))
    print("{0:d} datasets already have {1}".format(e_query.count(), kind.name))
    for dataset in query.all():
        print(dataset)
        dataset.update(session)
        if kind.h5path in dataset.telemetry and opt.force:
            dataset.telemetry[kind.h5path].remove()
        kind.generate(dataset)
        dataset.telemetry[kind.h5path] = Telemetry(kind=kind, dataset=dataset)
        session.add(dataset)
    session.commit()

if __name__ == '__main__':
    main()