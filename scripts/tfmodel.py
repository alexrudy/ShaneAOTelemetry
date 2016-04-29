#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
from telemetry.cli import parser
from telemetry.models import TelemetryKind, Telemetry, Dataset, TransferFunction, TransferFunctionFit
def setup(parser):
    """Set up the argument parser"""
    parser.add_argument("kind", type=str, help="Data kind to periodogram.")

def main():
    """Make transfer functions components."""
    opt = parser(setup)
    
    session = opt.session
    name = "transferfunctionmodel/{0}".format(opt.kind)
    tf_name = "transferfunction/{0}".format(opt.kind)
    kind = session.query(TelemetryKind).filter(TelemetryKind.h5path == name).one_or_none()
    if kind is None:
        session.add(TransferFunctionFit.from_telemetry_kind(opt.kind))
        session.commit()
        kind = session.query(TelemetryKind).filter(TelemetryKind.h5path == name).one()
    
    print(kind)
    if not hasattr(kind, 'generate'):
        opt.error("{0} does not appear to have a .generate() method.".format(type(kind).__name__))
    
    e_query = session.query(Dataset.id).join(Telemetry).join(TelemetryKind).filter(TelemetryKind.h5path == tf_name)
    t_query = session.query(Dataset.id).join(Telemetry).join(TelemetryKind).filter(TelemetryKind.h5path == name)
    query = session.query(Dataset).filter(Dataset.id.in_(e_query)).filter(Dataset.loop == "closed")
    
    if opt.date is not None:
        e_query = e_query.filter(Dataset.id.in_(opt.query))
        t_query = t_query.filter(Dataset.id.in_(opt.query))
        query = query.filter(Dataset.id.in_(opt.query))
    
    print("{0:d} potential target datasets.".format(query.count()))
    
    if not opt.force:
        query = query.filter(Dataset.id.notin_(t_query))
    
    print("Generating {0} for {1} datasets.".format(kind.name, query.count()))
    print("{0:d} datasets already have {1}".format(t_query.count(), kind.name))
    
    for dataset in query.all():
        if opt.force and kind.h5path in dataset.telemetry:
            dataset.telemetry[kind.h5path].remove()
        
        if not len(dataset.pairs):
            continue
        
        with dataset.open() as g:
            if kind.h5path in g:
                tel = dataset.telemetry[kind.name] = Telemetry(kind=kind, dataset=dataset)
                session.add(tel)
                continue
        kind.generate(dataset)
        dataset.telemetry[kind.name] = Telemetry(kind=kind, dataset=dataset)
        session.add(dataset.telemetry[kind.name])
        session.commit()
        session.refresh(dataset)
        print(dataset.telemetry[name])
    session.commit()

if __name__ == '__main__':
    main()