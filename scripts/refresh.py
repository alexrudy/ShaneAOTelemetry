#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
from telemetry.cli import parser
from telemetry.models import TelemetryKind, Dataset, Telemetry


def main():
    """Make various generated telemetry components."""
    opt = parser(None)
    
    session = opt.session
    for dataset in opt.query.all():
        dataset.update(session)
        print(dataset.telemetry.keys())
        session.add(dataset)
    session.commit()

if __name__ == '__main__':
    main()