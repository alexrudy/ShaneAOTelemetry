#!/usr/bin/env python

import sys, argparse, glob, os

import argparse
import datetime
from telemetry.cli import parser
from telemetry.models import Dataset, TransferFunctionPair, TransferFunction

def setup(parser):
    """Set up the argument parser"""
    pass

def main():
    """Make various generated telemetry components."""
    opt = parser(setup)
    session = opt.session
    
    s_attributes = {}
    sequence = None
    
    query = session.query(Dataset).filter(Dataset.id.in_(opt.query)).order_by(Dataset.created).filter(Dataset.loop == 'closed')
        
    print("Sequencing {0:d} datasets.".format(query.count()))
    iterator = iter(query.all())
    for dataset in iterator:
        other = dataset.match()
        if other is None:
            print("Couldn't match {0}".format(dataset))
            continue
        query_p = session.query(TransferFunctionPair)
        query_p = query_p.filter(TransferFunctionPair.loop_open_id == other.id)
        query_p = query_p.filter(TransferFunctionPair.loop_closed_id == other.id)
        pair = query_p.one_or_none()
        if pair is None:
            print("Matched {0}".format(dataset))
            print("To {0}".format(other))
            pair = TransferFunctionPair(loop_open=other, loop_closed=dataset)
        session.add(pair)
    session.commit()

if __name__ == '__main__':
    main()