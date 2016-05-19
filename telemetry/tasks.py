# -*- coding: utf-8 -*-
from __future__ import absolute_import

import glob
import os

import six
import h5py
from sqlalchemy.orm import object_session
from celery import chain, group
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from .application import app
from .models import Dataset, TelemetryKind, DatasetInfoBase, Instrument

@app.celery.task(bind=True)
def generate(self, dataset_id, telemetrykind_id, force=False):
    """A generate task."""
    kind = self.session.query(TelemetryKind).filter_by(id=telemetrykind_id).one()
    dataset = self.session.query(Dataset).filter_by(id=dataset_id).one()
    logger.info("Generating '{0}' from {1}".format(kind.h5path, dataset))
    if (kind.h5path in dataset.telemetry) and (force):
        logger.debug("Removed old telemetry {0}".format(kind.h5path))
        dataset.telemetry[kind.h5path].remove()
    if (kind.h5path not in dataset.telemetry) or (force):
        telemetry = kind.generate(dataset)
        self.session.add(telemetry)
    self.session.commit()
    return kind.h5path

def read_path(path, force=False):
    """Read many directories."""
    files = glob.iglob(os.path.expanduser(os.path.join(os.path.splitext(path)[0], '*.hdf5')))
    return group(read.si(fileanme, force) for filename in files)

@app.celery.task(bind=True)
def read(self, filename, force=False):
    """Given a directory, read it, looking for new datasets."""
    if not isinstance(filename, six.text_type):
        filename = filename.decode('utf-8')
        
    path_parts = os.path.abspath(filename).split(os.path.sep)
    instrument = Instrument.require(self.session, path_parts[-4])
    dataset = self.session.query(Dataset).filter(Dataset.filename == filename).one_or_none()
    if force and (dataset is not None):
        self.session.delete(dataset)
    if force or (dataset is None):
        with h5py.File(filename, mode='r') as f:
            dataset = Dataset.from_h5py_group(self.session, f['telemetry'])
            metadata = DatasetInfoBase.from_mapping(dataset, f['telemetry'].attrs, instrument=instrument.metadata_type)
            dataset.instrument = instrument
            self.session.add(metadata)
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
    
def rgenerate(dataset, telemetrykind, **kwargs):
    """Recursively generate using a celery chain."""
    c = chain(generate.si(dataset.id, prereq.id, **kwargs) for prereq in telemetrykind.rprerequisites[1:])
    return c