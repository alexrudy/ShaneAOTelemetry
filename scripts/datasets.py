#!/usr/bin/env python
from __future__ import print_function
import sys, argparse, glob, os
import datetime, itertools
import numpy as np

def dataset_table(query, keys=None, view=False):
    """From a query, construct a dataset table."""
    from astropy.table import Table
    if keys is None:
        keys = ["date", "mode", "substate", "loop", "gain", "wfs_rate", 
                "tweeter_bleed", "woofer_bleed", "alpha", "wfs_centroid", 
                "control_matrix", "reference_centroids"]
    t = Table([d.attributes() for d in query.all()])
    if view:
        t[keys].more()
    return t

def main():
    """Show all the datasets."""
    from telemetry.application import app
    from telemetry.models import Dataset, Telemetry, TelemetryKind
    from sqlalchemy.sql import between
    
    parser = argparse.ArgumentParser(description="View an ASCII table of datasets.")
    parser.add_argument("-d", "--date", type=lambda s : datetime.datetime.strptime(s, "%Y-%m-%d"), default=None)
    parser.add_argument("-k", "--kind", action='store_true', help="Show dataset kind matrix.")
    opt = parser.parse_args()
    
    with app.app_context():
        session = app.session
        query = session.query(Dataset)
        if opt.date is not None:
            start_date = opt.date#.date()
            end_date = (opt.date + datetime.timedelta(days=2))#.date()
            
            query = query.filter(between(Dataset.created,start_date,end_date))
    
        if not query.count():
            parser.error("Query returned no results for date range {0} to {1}".format(start_date, end_date))
    
        if not opt.kind:
            dataset_table(query, view=True)
        else:
            ndataset = query.count()
            ntop = session.query(TelemetryKind).count()
            keys = [ key for key, in session.query(TelemetryKind.h5path).all() ]
            matrix = np.zeros((ndataset, ntop), dtype=np.bool)
        
            for i,dataset in enumerate(query.all()):
                matrix[i,:] = [ (key in dataset.telemetry) for key in keys ]
            
            keys = np.asarray(keys)[np.any(matrix, axis=0)]
        
        
            for row in itertools.izip_longest(*keys, fillvalue=" "):
                print(" {} ".format(" ".join(row)))
        
            matrix = matrix[:,np.any(matrix, axis=0)]
            for row in matrix:
                print(np.array2string(row, max_line_width=120, formatter={'bool': lambda b : "T" if b else "F"}))
    
if __name__ == '__main__':
    main()