#!/usr/bin/env python
"""
Create telemetry objects from datasets.
"""

import sys, argparse, glob, os

def main():
    """Main function for parsing."""
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset, Slopes
    session = Session()
    
    n_telemetry = 0
    
    for dataset in session.query(Dataset).all():
        
        if not dataset.slopes:
            slopes = Slopes.from_dataset(dataset)
            session.add(slopes)
            n_telemetry += 1
    session.commit()
    print("Created {0:d} telemetry datasets.".format(n_telemetry))

if __name__ == '__main__':
    main()