# -*- coding: utf-8 -*-
from __future__ import absolute_import

import glob
import os

import six
import h5py
from sqlalchemy.orm import object_session
from celery import chain, group
from celery.utils.log import get_task_logger
from astropy.utils.console import ProgressBar
logger = get_task_logger(__name__)

from .application import app
from .models import Dataset, TelemetryKind

def progress(resultset):
    """A group result progressbar."""
    try:
        with ProgressBar(len(resultset)) as pbar:
            pbar.update(0)
            while not resultset.ready():
                pbar.update(resultset.completed_count())
                time.sleep(0.1)
            pbar.update(resultset.completed_count())
    except KeyboardInterrupt as e:
        resultset.revoke()
        raise
    else:
        # Raise the error, if there was one.
        if resultset.failed():
            resultset.get()
    return

@app.celery.task(bind=True)
def generate(self, dataset_id, telemetrykind_id):
    """A generate task."""
    kind = self.session.query(TelemetryKind).filter_by(id=telemetrykind_id).one()
    dataset = self.session.query(Dataset).filter_by(id=dataset_id).one()
    logger.info("IDs {0} and {1}".format(telemetrykind_id, dataset_id))
    logger.info("Generating '{0}' from {1}".format(kind.h5path, dataset))
    if kind.h5path not in dataset.telemetry:
        telemetry = kind.generate(dataset)
        self.session.add(telemetry)
    self.session.commit()

def read_path(path, force=False):
    """Read many directories."""
    files = glob.iglob(os.path.expanduser(os.path.join(os.path.splitext(path)[0], '*.hdf5')))
    return group(read.si(fileanme, force) for filename in files)

@app.celery.task(bind=True)
def read(self, filename, force=False):
    """Given a directory, read it, looking for new datasets."""
    if not isinstance(filename, six.text_type):
        filename = filename.decode('utf-8')
    dataset = self.session.query(Dataset).filter(Dataset.filename == filename).one_or_none()
    if force and (dataset is None):
        self.session.delete(dataset)
    if force or (dataset is None):
        with h5py.File(filename, mode='r') as f:
            dataset = Dataset.from_h5py_group(self.session, f['telemetry'])
    dataset.update(self.session)
    self.session.add(dataset)
    self.session.commit()

@app.celery.task(bind=True)
def refresh(self, dataset_id):
    """Refresh a given dataset id."""
    dataset = self.session.query(Dataset).filter_by(id=dataset_id).one()
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
    c = chain(generate.si(dataset.id, prereq.id) for prereq in telemetrykind.rprerequisites[1:])
    return c