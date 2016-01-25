#!/usr/bin/env python
"""
Create telemetry objects from datasets.
"""

import sys, argparse, glob, os

def main():
    """Main function for parsing."""
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset, Periodogram, PeriodogramStack, Sequence
    session = Session()
    
    n_telemetry = 0
    
    for sequence in session.query(Sequence).all():
        
        if not sequence.periodograms:
            pgram = PeriodogramStack.from_sequence(sequence, 'slopes', 1024)
            session.add(pgram)
            n_telemetry += 1
    session.commit()
    print("Created {0:d} periodograms.".format(n_telemetry))

if __name__ == '__main__':
    main()