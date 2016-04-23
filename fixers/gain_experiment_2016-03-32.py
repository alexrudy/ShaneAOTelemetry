#!/usr/bin/env python
from __future__ import print_function
import sys, argparse, glob, os, datetime


DEFAULT_MATRIX = "controlMatrix_16x.fits"
BOOSTED_MATRIX = "controlMatrix_16x.incgain.RUDY.fits"

CM_RANGES = [
    (3, 22, DEFAULT_MATRIX),
    (23, 42, BOOSTED_MATRIX),
    (43, 62, DEFAULT_MATRIX),
    (63, 82, BOOSTED_MATRIX),
    (83, 102, DEFAULT_MATRIX),
    (103,122, BOOSTED_MATRIX),
    (123,142, DEFAULT_MATRIX),
    (143,162, BOOSTED_MATRIX),
    (163,182, DEFAULT_MATRIX),
    (183,195, BOOSTED_MATRIX),
    (196,215, DEFAULT_MATRIX),
    (216,235, BOOSTED_MATRIX),
    (236,255, DEFAULT_MATRIX),
    (256,275, BOOSTED_MATRIX),
    (276,295, DEFAULT_MATRIX),
    (296,315, BOOSTED_MATRIX),
    (316,335, DEFAULT_MATRIX),
    (336,355, BOOSTED_MATRIX),
    (356,375, DEFAULT_MATRIX),
    (376,395, BOOSTED_MATRIX),
    (396,425, DEFAULT_MATRIX),
    (426,445, BOOSTED_MATRIX)
]

index = max(items[1] for items in CM_RANGES) + 1
for start, stop, cm in CM_RANGES:
    if stop == index - 1:
        last = cm
        nex = BOOSTED_MATRIX if last == DEFAULT_MATRIX else DEFAULT_MATRIX
        break

while index <= 556:
    CM_RANGES.append((index, index+19, nex))
    nex, last = last, nex
    index += 20

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
    start_date = datetime.datetime(2016,03,24,0,0,0)
    end_date = start_date + datetime.timedelta(days=1)
    try:
        for dataset in session.query(Dataset).filter(between(Dataset.created,start_date,end_date)).filter(Dataset.sequence_number >= 3).all():
            dataset.control_matrix = find_cm(dataset.sequence_number)
            print("{:d}: {:s} {} {}".format(dataset.sequence_number, dataset, dataset.created, dataset.control_matrix))
            session.add(dataset)
    finally:
        session.commit()

if __name__ == '__main__':
    main()