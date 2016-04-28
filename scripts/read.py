#!/usr/bin/env python
from __future__ import print_function
import sys, argparse, glob, os
import h5py
import six
import itertools

def main():
    """Main function for parsing."""
    from telemetry import connect
    from telemetry.models import Dataset
    session = connect()()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="Path names.")
    parser.add_argument("-f", "--force", action='store_true', help="Force read all datasets.")
    opt = parser.parse_args()
    new_datasets = 0
    directories = set()
    paths = itertools.imap(lambda path : os.path.expanduser(os.path.join(os.path.splitext(path)[0], '*.hdf5')), opt.paths)
    paths = itertools.chain.from_iterable(itertools.imap(glob.iglob, paths))
    
    for filename in paths:
        if not isinstance(filename, six.text_type):
            filename = filename.decode('utf-8')
        dataset = session.query(Dataset).filter(Dataset.filename == filename).one_or_none()
        if opt.force and (dataset is None):
            session.delete(dataset)
        if (dataset is None) or opt.force:
            if os.path.dirname(filename) not in directories:
                print("Importing from '{0:s}'".format(os.path.dirname(filename)))
                directories.add(os.path.dirname(filename))
            
            with h5py.File(filename, mode='r') as f:
                dataset = Dataset.from_h5py_group(session, f['telemetry'])
        dataset.update(session)
        session.add(dataset)
    print("Added {:d} datasets.".format(len(session.new)))
    session.commit()


if __name__ == '__main__':
    main()