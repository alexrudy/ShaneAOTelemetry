#!/usr/bin/env python
from __future__ import print_function
import sys, argparse, glob, os
import h5py
import six
import itertools

def main():
    """Main function for parsing."""
    from telemetry.application import app
    from telemetry.models import Dataset
    parser = argparse.ArgumentParser()
    default_path = os.path.join(app.config['TELEMETRY_ROOTDIRECTORY'], "**", "**", "raw")
    parser.add_argument("paths", nargs="*", help="Path names.", default=[default_path])
    parser.add_argument("-f", "--force", action='store_true', help="Force read all datasets.")
    opt = parser.parse_args()
    
    with app.app_context():
        
        new_datasets = 0
        directories = set()
        paths = itertools.imap(lambda path : os.path.expanduser(os.path.join(os.path.splitext(path)[0], '*.hdf5')), opt.paths)
        paths = itertools.chain.from_iterable(itertools.imap(glob.iglob, paths))
    
        for filename in paths:
            if not isinstance(filename, six.text_type):
                filename = filename.decode('utf-8')
            dataset = app.session.query(Dataset).filter(Dataset.filename == filename).one_or_none()
            if opt.force and (dataset is None):
                app.session.delete(dataset)
            if (dataset is None) or opt.force:
                if os.path.dirname(filename) not in directories:
                    print("Importing from '{0:s}'".format(os.path.dirname(filename)))
                    directories.add(os.path.dirname(filename))
            
                with h5py.File(filename, mode='r') as f:
                    dataset = Dataset.from_h5py_group(app.session, f['telemetry'])
            dataset.update(app.session)
            app.session.add(dataset)
        print("Added {:d} datasets.".format(len(app.session.new)))
        app.session.commit()


if __name__ == '__main__':
    main()