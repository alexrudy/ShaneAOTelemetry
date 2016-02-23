#!/usr/bin/env python

import sys, argparse, glob, os

def main():
    """Main function for parsing."""
    parser = argparse.ArgumentParser()
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
    
    if opt.force:
        print("Removing previous sequences.")
        session.query(Sequence).delete()
    
    print("Sequencing {0:d} datasets.".format(session.query(Dataset).count()))
    for dataset in ProgressBar(session.query(Dataset).all()):
        if dataset.get_sequence_attributes() != s_attributes:
            sequence = Sequence(**dataset.get_sequence_attributes()) if dataset.sequence is None else dataset.sequence
            sequence.number = dataset.sequence_number
            s_attributes = sequence.get_sequence_attributes()
        dataset.sequence = sequence
    session.commit()
    
    print("Matching {0:d} datasets.".format(session.query(Sequence).count()))
    for sequence in ProgressBar(session.query(Sequence).all()):
        pair = sequence.match_sequence()
        session.add(sequence)
    session.commit()
    
    if opt.verbose:
        for sequence in session.query(Sequence).all():
            dataset = sequence.datasets[0]
            print("{:3d} = {:4d} - {:3d} ({:3d}) -> {:3d} : {:.2f} {:s}".format(sequence.id, dataset.sequence_number, dataset.sequence_number+len(sequence.datasets), len(sequence.datasets), sequence.pair_id, sequence.gain, sequence.loop))

if __name__ == '__main__':
    main()