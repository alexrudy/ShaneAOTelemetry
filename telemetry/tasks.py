# -*- coding: utf-8 -*-
from __future__ import absolute_import
from sqlalchemy.orm import sessionmaker, scoped_session, object_session
from .application import app
from .models import Dataset, TelemetryKind
from celery import chain
import six

@app.celery.task(bind=True)
def generate(self, dataset_id, telemetrykind_id):
    """A generate task."""
    try:
        kind = self.sesion.query(TelemetryKind).get(telemetrykind_id)
        dataset = self.session.query(Dataset).get(dataset_id)
        telemetry = kind.generate(dataset)
        self.session.add(telemetry)
    except Exception:
        self.session.rollback()
        raise
    else:
        self.session.commit()
        
    
@app.celery.task(bind=True)
def read(self, directory):
    """Given a directory, read it, looking for new datasets."""
    import glob, os
    files = glob.iglob(os.path.expanduser(os.path.join(os.path.splitext(path)[0], '*.hdf5')))
    for filename in files:
        if not isinstance(filename, six.text_type):
            filename = filename.decode('utf-8')
        dataset = self.session.query(Dataset).filter(Dataset.filename == filename).one_or_none()
        if opt.force and (dataset is None):
            self.session.delete(dataset)
        if (dataset is None) or opt.force:
            if os.path.dirname(filename) not in directories:
                print("Importing from '{0:s}'".format(os.path.dirname(filename)))
                directories.add(os.path.dirname(filename))
        
            with h5py.File(filename, mode='r') as f:
                dataset = Dataset.from_h5py_group(self.session, f['telemetry'])
        dataset.update(app.session)
        self.session.add(dataset)
    self.session.commit()

@app.celery.task(bind=True)
def refresh(self, dataset_id):
    """Refresh a given dataset id."""
    dataset = self.session.query(Dataset).get(dataset_id)
    try:
        dataset.update()
    except Exception:
        self.session.rollback()
        raise
    else:
        self.session.commit()
    return dataset.id
    
def rgenerate(dataset, telemetrykind):
    """Recursively generate using a celery chain."""
    session = object_session(telemetrykind)
    c = chain(*[ generate.si(dataset.id, prereq.id) for prereq in telemetrykind.rprequisites ])
    return c