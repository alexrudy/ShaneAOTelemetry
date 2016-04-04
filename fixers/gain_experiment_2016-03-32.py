#!/usr/bin/env python
from __future__ import print_function
import sys, argparse, glob, os, datetime

CM_RANGES = [
    (3, 22, "Default"),
    (23, 42, "Rudy"),
    (43, 62, "Default"),
    (63, 82, "Rudy"),
    (83, 102, "Default"),
    (103,122, "Rudy"),
    (123,142, "Default"),
    (143,162, "Rudy"),
    (163,182, "Default"),
    (183,195, "Rudy"),
    (196,215, "Default"),
    (216,235, "Rudy"),
    (236,255, "Default"),
    (256,275, "Rudy"),
    (276,295, "Default"),
    (296,315, "Rudy"),
    (316,335, "Default"),
    (336,355, "Rudy"),
    (356,375, "Default"),
    (376,395, "Rudy"),
    (396,425, "Default"),
    (426,445, "Rudy")
]

index = max(items[1] for items in CM_RANGES) + 1
for start, stop, cm in CM_RANGES:
    if stop == index - 1:
        last = cm
        nex = "Rudy" if last == "Default" else "Default"
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