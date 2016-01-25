#!/usr/bin/env python
from __future__ import print_function
import sys, argparse, glob, os

def main():
    """Main function for parsing."""
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset
    session = Session()
    new_datasets = 0
    directories = set()
    for filename in glob.iglob(os.path.join(sys.argv[1], '*.fits')):
        if not session.query(Dataset).filter(Dataset.filename == filename).count():
            if os.path.dirname(filename) not in directories:
                print("Importing from '{0:s}'".format(os.path.dirname(filename)))
                directories.add(filename)
            
            dataset = Dataset.from_filename(filename)
            session.add(dataset)
            new_datasets += 1
    print("Added {:d} datasets.".format(new_datasets))
    session.commit()


if __name__ == '__main__':
    main()