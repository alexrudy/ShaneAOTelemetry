#!/usr/bin/env python

import sys, argparse, glob, os

def main():
    """Main function for parsing."""
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset, Sequence
    from astropy.utils.console import ProgressBar
    from sqlalchemy.sql import func
    
    session = Session()
    
    s_attributes = {}
    sequence = None
    
    for dataset in ProgressBar(session.query(Dataset).all()):
        if dataset.get_sequence_attributes() != s_attributes:
            sequence = Sequence(**dataset.get_sequence_attributes()) if dataset.sequence is None else dataset.sequence
            sequence.number = dataset.sequence_number
            s_attributes = sequence.get_sequence_attributes()
        dataset.sequence = sequence
    session.commit()
    
    for sequence in ProgressBar(session.query(Sequence).all()):
        attrs = sequence.matched_pair_attributes()
        matchq = session.query(Sequence).filter_by(**attrs).filter(Sequence.id != sequence.id).filter(Sequence.loop != sequence.loop)
        matches = matchq.order_by(func.abs(Sequence.number - sequence.number)).all()
        closest = min(abs(s.number - sequence.number) for s in matches)
        matches = filter(lambda s : abs(s.number - sequence.number) <= closest, matches)
        matches.sort(key=lambda m : abs(len(m.datasets) - len(sequence.datasets)))
        sequence.pair = matches[0]
        session.add(sequence)
    session.commit()
    
    for sequence in session.query(Sequence).all():
        dataset = sequence.datasets[0]
        print("{:3d} = {:4d} - {:3d} ({:3d}) -> {:3d} : {:.2f} {:s}".format(sequence.id, dataset.sequence_number, dataset.sequence_number+len(sequence.datasets), len(sequence.datasets), sequence.pair_id, sequence.gain, sequence.loop))

if __name__ == '__main__':
    main()