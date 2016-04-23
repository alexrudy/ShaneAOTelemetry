#!/usr/bin/env python
from __future__ import print_function
import sys, argparse, glob, os, datetime

DEFAULT_MATRIX = "controlMatrix_16x.fits"
DEFAULT_REFCENTS = "refcents_16x.fits"
CM_RANGES = [
    (6, 55, (DEFAULT_MATRIX, DEFAULT_REFCENTS)),
    (56, 105, (DEFAULT_MATRIX, DEFAULT_REFCENTS)),
    (106, 155, ("controlMatrix_16x.incgain.250Hz.fits", DEFAULT_REFCENTS)),
    (156, 203, ("controlMatrix_16x.incgain.1000Hz.fits", DEFAULT_REFCENTS)),
    (204, 253, (DEFAULT_MATRIX, DEFAULT_REFCENTS)),
    (254, 303, (DEFAULT_MATRIX, "refcents_16x.1000Hz.fits")),
    (304, 353, ("controlMatrix_16x.incgain.250Hz.fits", DEFAULT_REFCENTS)),
    (354, 403, ("controlMatrix_16x.incgain.250Hz.fits", "refcents_16x.1000Hz.fits")),
    (404, 453, ("controlMatrix_16x.incgain.1000Hz.fits", "refcents_16x.1000Hz.fits")),
    (454, 503, (DEFAULT_MATRIX, DEFAULT_REFCENTS)),
    (504, 553, (DEFAULT_MATRIX, DEFAULT_REFCENTS)),
    (554, 603, (DEFAULT_MATRIX, "refcents_16x.1000Hz.fits")),
    (604, 653, ("controlMatrix_16x.incgain.250Hz.fits", DEFAULT_REFCENTS)),
    (654, 753, ("controlMatrix_16x.incgain.250Hz.fits", "refcents_16x.1000Hz.fits")),
    (754, 803, ("controlMatrix_16x.incgain.250Hz.fits", DEFAULT_REFCENTS)),
    (804, 1023,(DEFAULT_MATRIX, DEFAULT_REFCENTS)),
    
]

def find_cm(index):
    """Find the CM, the dumb way."""
    for start, stop, name in CM_RANGES:
        if start <= index <= stop:
            return name
    else:
        raise ValueError("Couldn't figure it out.")

def main():
    """Show all the datasets."""
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset, Sequence
    from sqlalchemy.sql import between
    session = Session()
    start_date = datetime.datetime(2016,04,18,0,0,0)
    end_date = start_date + datetime.timedelta(days=2)
    try:
        for dataset in session.query(Dataset).filter(between(Dataset.created,start_date,end_date)).filter(Dataset.sequence_number >= 3).all():
            try:
                cm, ref = find_cm(dataset.sequence_number)
            except ValueError as e:
                pass
            else:
                dataset.control_matrix = cm
                dataset.refcents = ref
                print("{:d}: {:s} {} {} {}".format(dataset.sequence_number, dataset, dataset.created, dataset.control_matrix, dataset.refcents))
                session.add(dataset)
    finally:
        session.commit()

if __name__ == '__main__':
    main()