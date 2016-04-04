#!/usr/bin/env python

import sys, argparse, glob, os

def main():
    """Main function for parsing."""
    parser = argparse.ArgumentParser(description="Used to fix sequence objects if their constituent dataset attributes are updated.")
    parser.add_argument("-q", "--quiet", action='store_false', dest='verbose', help="Quiet the script")
    parser.add_argument("-f", "--force", action='store_true', help="Force")
    
    opt = parser.parse_args()
    
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset, Sequence
    from astropy.utils.console import ProgressBar
    
    session = Session()
    
    s_attributes = {}
    sequence = None
    
    
    print("Fixing {0:d} datasets.".format(session.query(Sequence).count()))
    for sequence in ProgressBar(session.query(Sequence).all()):
        dataset = sequence.datasets[0]
        for attr, value in dataset.get_sequence_attributes().items():
            setattr(sequence, attr, value)
        session.add(sequence)
    session.commit()
    

if __name__ == '__main__':
    main()
