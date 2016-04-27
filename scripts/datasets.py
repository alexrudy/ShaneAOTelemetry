#!/usr/bin/env python
from __future__ import print_function
import sys, argparse, glob, os
import datetime

def main():
    """Show all the datasets."""
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset, Telemetry, TelemetryKind
    from sqlalchemy.sql import between
    from astropy.table import Table
    
    parser = argparse.ArgumentParser(description="View an ASCII table of datasets.")
    parser.add_argument("date", type=lambda s : datetime.datetime.strptime(s, "%Y-%m-%d"))
    parser.add_argument("kind", nargs="?", help="Show dataset kinds.", default=None)
    opt = parser.parse_args()
    start_date = opt.date#.date()
    end_date = (opt.date + datetime.timedelta(days=2))#.date()
    
    session = Session()
    query = session.query(Dataset).filter(between(Dataset.created,start_date,end_date))
    if not query.count():
        parser.error("Query returned no results for date range {0} to {1}".format(start_date, end_date))
    if opt.kind is None:
        datasets = query.all()
        t = Table([d.attributes() for d in datasets])
        t[["date", "mode", "loop", "gain", "wfs_rate", "tweeter_bleed", "woofer_bleed", "alpha", "wfs_centroid", "control_matrix", "reference_centroids"]].pprint()
    else:
        query = query.join(Telemetry).join(TelemetryKind).filter(TelemetryKind.h5path == opt.kind)
        if not query.count():
            print("No matching datasets found!")
        for dataset in query.all():
            print("{0!r}: {1}".format(dataset, ",".join(dataset.telemetry.keys())))
    
if __name__ == '__main__':
    main()