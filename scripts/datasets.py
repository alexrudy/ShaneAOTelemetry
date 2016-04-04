#!/usr/bin/env python
from __future__ import print_function
import sys, argparse, glob, os
import datetime

def main():
    """Show all the datasets."""
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset, Sequence
    from sqlalchemy.sql import between
    
    parser = argparse.ArgumentParser(description="View an ASCII table of datasets.")
    parser.add_argument("date", type=lambda s : datetime.datetime.strptime(s, "%Y-%m-%d"))
    opt = parser.parse_args()
    start_date = opt.date
    end_date = opt.date + datetime.timedelta(days=1)
    
    session = Session()
    query = session.query(Dataset).filter(between(Dataset.created,start_date,end_date))
    for dataset in .all():
        print("{:d}: {:s} {:}".format(dataset.sequence_number, dataset, dataset.created))

if __name__ == '__main__':
    main()