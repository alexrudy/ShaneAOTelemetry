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
    kind = session.query(TelemetryKind).filter(TelemetryKind.name == opt.kind).one_or_none()
    if kind is None:
        session.add(TelemetryKind(name=opt.kind, h5path=opt.kind))
        session.commit()
        kind = session.query(TelemetryKind).filter(TelemetryKind.name == opt.kind).one()
    
    if not hasattr(kind, 'generate'):
        opt.error("{0} does not appear to have a .generate() method.".format(type(kind).__name__))
    
    e_query = session.query(Dataset.id).join(Dataset.kinds).filter(TelemetryKind.name == opt.kind)
    if not opt.force:
        query = opt.query.filter(~Dataset.id.in_(e_query))
    else:
        query = opt.query
    
    for dataset in query.all():
        if kind.name in dataset.telemetry and opt.force:
            dataset.telemetry[kind.name].remove()
        kind.generate(dataset)
        dataset.telemetry[kind.name] = Telemetry(kind=kind, dataset=dataset)
        session.add(dataset)
    session.commit()

if __name__ == '__main__':
    main()