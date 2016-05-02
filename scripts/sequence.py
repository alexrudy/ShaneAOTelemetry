#!/usr/bin/env python

import sys, argparse, glob, os

import argparse
import datetime
from telemetry.cli import parser, resultset_progress
from telemetry.application import app
from telemetry.models import Dataset
from telemetry.fourieranalysis.tasks import pair
from celery import group

def setup(parser):
    """Set up the argument parser"""
    pass

def main():
    """Make various generated telemetry components."""
    opt = parser(setup)
    
    with app.app_context():
        query = app.session.query(Dataset).order_by(Dataset.created).filter(Dataset.loop == 'closed')
        print("Sequencing {0:d} datasets.".format(query.count()))
        g = group(pair.si(dataset.id) for dataset in query.all())
        resultset_progress(g.delay())


if __name__ == '__main__':
    main()