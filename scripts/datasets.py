#!/usr/bin/env python
from __future__ import print_function
import sys, argparse, glob, os
import datetime

def main():
    """Show all the datasets."""
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset
    from sqlalchemy.sql import between
    from astropy.table import Table
    
    parser = argparse.ArgumentParser(description="View an ASCII table of datasets.")
    parser.add_argument("date", type=lambda s : datetime.datetime.strptime(s, "%Y-%m-%d"))
    opt = parser.parse_args()
    start_date = opt.date#.date()
    end_date = (opt.date + datetime.timedelta(days=2))#.date()
    
    session = Session()
    query = session.query(Dataset).filter(between(Dataset.created,start_date,end_date))
    if not query.count():
        parser.error("Query returned no results for date range {0} to {1}".format(start_date, end_date))
    datasets = query.all()
    
    print(set(k for d in datasets for k in d.telemetry.keys()))
    
    t = Table([d.attributes() for d in datasets])
    t[["date", "mode", "loop", "gain", "wfs_rate", "tweeter_bleed", "woofer_bleed", "alpha", "wfs_centroid", "control_matrix", "reference_centroids"]].pprint()
    
if __name__ == '__main__':
    main()