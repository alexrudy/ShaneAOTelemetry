#!/usr/bin/env python

import sys, argparse, glob, os

def main():
    """Main function for parsing."""
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset, Sequence
    session = Session()
    
    s_attributes = {}
    sequence = None
    
    for dataset in session.query(Dataset).all():
        if dataset.get_sequence_attributes() != s_attributes:
            sequence = Sequence() if dataset.sequence is None else dataset.sequence
            s_attributes = dataset.get_sequence_attributes()
        dataset.sequence = sequence
    session.commit()
    
    for sequence in session.query(Sequence).all():
        dataset = sequence.datasets[0]
        print("{:3d} = {:4d} - {:3d} ({:3d}) : {:.2f} {:s}".format(sequence.id, dataset.sequence_number, dataset.sequence_number+len(sequence.datasets), len(sequence.datasets), sequence.gain, sequence.loop))

if __name__ == '__main__':
    main()