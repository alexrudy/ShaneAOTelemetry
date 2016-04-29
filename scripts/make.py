#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
import collections
from telemetry.cli import parser
from telemetry.models import TelemetryKind, Dataset, Telemetry
from astropy.utils.console import ProgressBar

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
    
    session = opt.session
    kind = get_kind(session, opt.kind)
    print(kind)
    if not hasattr(kind, 'generate'):
        opt.error("{0} does not appear to have a .generate() method.".format(type(kind).__name__))
    prerequisties = kind.rprerequisites
    
    done = session.query(Dataset.id).join(Dataset.kinds).filter(TelemetryKind.h5path == prerequisties[-1].h5path)
    if opt.recursive:
        query = session.query(Dataset).join(Dataset.kinds).filter(TelemetryKind.h5path == prerequisties[0].h5path)
        for p in prerequisties:
            query = p.filter(query)
    else:
        query = session.query(Dataset).join(Dataset.kinds).filter(TelemetryKind.h5path == prerequisties[-2].h5path)
        query = kind.filter(query)
    
    if not opt.force:
        query = query.filter(Dataset.id.notin_(done))
    
    if opt.date:
        query.filter(Dataset.id.in_(opt.query))
    
    print(opt.date)
    print("Generating {0} for {1} datasets.".format(kind.name, query.count()))
    print("{0:d} datasets already have {1}".format(done.count(), kind.name))
    
    try:
        for dataset in ProgressBar(query.all()):
            new_telemetry = kind.rgenerate(session, dataset, force=opt.force)
            session.add(dataset)
    except KeyboardInterrupt:
        print("Committing after keyboard interrupt.")
        session.commit()
        raise
    else:
        session.commit()

if __name__ == '__main__':
    main()