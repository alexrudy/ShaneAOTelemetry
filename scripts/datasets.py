#!/usr/bin/env python
from __future__ import print_function
import sys, argparse, glob, os
import datetime

def _make_row(ds):
    """Make a table row."""
    row = ds.get_sequence_attributes()
    row['CM'] = row.pop('control_matrix')
    # row['date'] = row['date']
    # row['gain'] = ds.gain
    row["n"] = ds.sequence_number
    return row

def main():
    """Show all the datasets."""
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset, Sequence
    from sqlalchemy.sql import between
    from astropy.table import Table
    
    parser = argparse.ArgumentParser(description="View an ASCII table of datasets.")
    parser.add_argument("date", type=lambda s : datetime.datetime.strptime(s, "%Y-%m-%d"))
    opt = parser.parse_args()
    start_date = opt.date
    end_date = opt.date + datetime.timedelta(days=2)
    
    session = Session()
    query = session.query(Dataset).filter(between(Dataset.created,start_date,end_date))
    rows = []
    for dataset in query:
        rows.append(_make_row(dataset))
    t = Table(rows)
    t.pprint()
    t.write("datasets.txt", format='ascii.fixed_width')
    
if __name__ == '__main__':
    main()