#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
from telemetry.cli import parser
from telemetry.models import Dataset


def main():
    """Make various generated telemetry components."""
    opt = parser(None)
    
    session = opt.session
    query = opt.filter(session.query(Dataset))
    for dataset in query.all():
        dataset.update(session)
        print(dataset.telemetry.keys())
        session.add(dataset)
    session.commit()

if __name__ == '__main__':
    main()