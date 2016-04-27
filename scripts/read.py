#!/usr/bin/env python
from __future__ import print_function
import sys, argparse, glob, os
import h5py
import six

def main():
    """Main function for parsing."""
    from telemetry import connect
    from telemetry.models import Dataset
    session = connect()()
    
    new_datasets = 0
    directories = set()
    for path in sys.argv[1:]:
        path = os.path.splitext(path)[0]
        query_path = os.path.expanduser(os.path.join(path, '*.hdf5'))
        print("Importing files which match '{0}'".format(query_path))
        for filename in glob.iglob(query_path):
            if not isinstance(filename, six.text_type):
                filename = filename.decode('utf-8')
            dataset = session.query(Dataset).filter(Dataset.filename == filename).one_or_none()
            if dataset is None:
                if os.path.dirname(filename) not in directories:
                    print("Importing from '{0:s}'".format(os.path.dirname(filename)))
                    directories.add(os.path.dirname(filename))
                
                with h5py.File(filename) as f:
                    dataset = Dataset.from_h5py_group(session, f['telemetry'])
            dataset.update(session)
            session.add(dataset)
    print("Added {:d} datasets.".format(len(session.new)))
    session.commit()


if __name__ == '__main__':
    main()