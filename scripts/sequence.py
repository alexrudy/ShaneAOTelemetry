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
        session.commit()
    
    for sequence in session.query(Sequence).all():
        if not len(sequence.datasets):
            session.delete(sequence)
    
    print("Sequencing {0:d} datasets.".format(session.query(Dataset).count()))
    iterator = ProgressBar(session.query(Dataset).all())
    for dataset in session.query(Dataset).all():
        d_attributes = dataset.get_sequence_attributes()
        if d_attributes != s_attributes:
            changed = []
            for key, value in s_attributes.items():
                if d_attributes[key] != value:
                    changed.append((key, value, d_attributes[key]))
            print("{} Changed: {}".format(dataset.sequence_number, " ".join(["{}={}->{}".format(key, old, new) for key, old, new in changed])))
            if dataset.sequence:
                ds_attributes = dataset.sequence.get_sequence_attributes()
                if ds_attributes != s_attributes:
                    sequence = Sequence(**d_attributes)
                    sequence.number = dataset.sequence_number
                    session.add(sequence)
                else:
                    sequence = dataset.sequence
            s_attributes = sequence.get_sequence_attributes()
        dataset.sequence = sequence
        session.add(dataset)
    session.commit()
    
    print("Matching {0:d} datasets.".format(session.query(Sequence).count()))
    for sequence in ProgressBar(session.query(Sequence).all()):
        if not len(sequence.datasets):
            session.delete(sequence)
            continue
        pair = sequence.match_sequence()
        session.add(sequence)
    session.commit()
    
    if opt.verbose:
        for sequence in session.query(Sequence).all():
            if not len(sequence.datasets):
                session.delete(sequence)
                continue 
            dataset = sequence.datasets[0]
            pair_id = "{:3d}".format(sequence.pair_id) if sequence.pair_id is not None else "N/A"
            print("{:3d} = {:4d} - {:3d} ({:3d}) -> {:s} : {:.2f} {:s} {:s} {:s}".format(sequence.id, dataset.sequence_number, dataset.sequence_number+len(sequence.datasets), len(sequence.datasets), pair_id, sequence.gain, sequence.loop, sequence.control_matrix, sequence.refcents))

if __name__ == '__main__':
    main()