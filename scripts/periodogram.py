#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
from telemetry.cli import parser
from telemetry.models import TelemetryKind, Telemetry, Dataset, Periodogram
def setup(parser):
    """Set up the argument parser"""
    parser.add_argument("kind", type=str, help="Data kind to periodogram.")

def main():
    """Make various generated telemetry components."""
    opt = parser(setup)
    
    session = opt.session
    name = "{0} periodogram".format(opt.kind)
    kind = session.query(TelemetryKind).filter(TelemetryKind.name == name).one_or_none()
    if kind is None:
        session.add(Periodogram.from_telemetry_kind(opt.kind))
        session.commit()
        kind = session.query(TelemetryKind).filter(TelemetryKind.name == name).one()
    
    print(kind)
    if not hasattr(kind, 'generate'):
        opt.error("{0} does not appear to have a .generate() method.".format(type(kind).__name__))
    
    e_query = session.query(Dataset.id).join(Dataset.kinds).filter(TelemetryKind.name == opt.kind)
    p_query = session.query(Dataset.id).join(Dataset.kinds).filter(TelemetryKind.name == name)
    
    query = opt.query.filter(Dataset.id.in_(e_query))
    if not opt.force:
        query = query.filter(~Dataset.id.in_(p_query))
    for dataset in query.all():
        if opt.force and kind.name in dataset.telemetry:
            dataset.telemetry[kind.name].remove()
        
        with dataset.open() as g:
            if kind.h5path in g:
                dataset.telemetry[kind.name] = Telemetry(kind=kind, dataset=dataset)
                session.add(dataset.telemetry[kind.name])
                continue
        kind.generate(dataset, 1024, half_overlap=False)
        dataset.telemetry[kind.name] = Telemetry(kind=kind, dataset=dataset)
        session.add(dataset.telemetry[kind.name])
        session.commit()
        session.refresh(dataset)
        print(dataset.telemetry[name])
    session.commit()

if __name__ == '__main__':
    main()