# -*- coding: utf-8 -*-
from __future__ import absolute_import

import glob
import os

import six
import h5py
from sqlalchemy.orm import object_session
from celery import chain, group
from celery.utils.log import get_task_logger
log = get_task_logger(__name__)

from .application import app
from .models import Dataset, TelemetryKind, DatasetInfoBase, Instrument

@app.celery.task(bind=True)
def generate(self, dataset_id, telemetrykind_id, force=False):
    """A generate task."""
    kind = self.session.query(TelemetryKind).filter_by(id=telemetrykind_id).one()
    dataset = self.session.query(Dataset).filter_by(id=dataset_id).one()
    log.info("Generating '{0}' from {1}".format(kind.h5path, dataset))
    if (kind.h5path in dataset.telemetry) and (force):
        log.debug("Removed old telemetry {0}".format(kind.h5path))
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
def read(self, filename, instrument_name=None, force=False):
    """Given a directory, read it, looking for new datasets."""
    if not isinstance(filename, six.text_type):
        filename = filename.decode('utf-8')
    filename = os.path.abspath(filename)
    
    path_parts = filename.split(os.path.sep)
    path_root = os.path.abspath(app.config['TELEMETRY_ROOTDIRECTORY'])
    if instrument_name is None:
        if filename.startswith(path_root):
            n_parts = len(path_root.split(os.path.sep))
            instrument_name = path_parts[n_parts]
        else:
            instrument_name = path_parts[-4]
    instrument = Instrument.require(self.session, instrument_name)
    dataset = self.session.query(Dataset).filter(Dataset.filename == filename).one_or_none()
    if force and (dataset is not None):
        self.session.delete(dataset)
    if force or (dataset is None):
        log.info("Opening {0}".format(filename))
        with self.redis.lock(filename, timeout=1000):
            with h5py.File(filename, mode='r') as f:
                if 'telemetry' not in f:
                    log.error("Expected to find a '/telemetry' group. Found [{0}]".format(",".join(f.keys())))
                    raise KeyError('telemetry')
                dataset = Dataset.from_h5py_group(self.session, f['telemetry'])
                metadata = DatasetInfoBase.from_mapping(dataset, f['telemetry'].attrs, instrument=instrument.metadata_type)
                dataset.instrument = instrument
                dataset.update_h5py_group(self.session, f['telemetry'])
                self.session.add(metadata)
    dataset.update(self.session)
    self.session.add(dataset)
    self.session.commit()
    return dataset.id

@app.celery.task(bind=True)
def refresh(self, dataset_id, validate=False):
    """Refresh a given dataset id."""
    dataset = self.session.query(Dataset).filter_by(id=dataset_id).one()
    if validate:
        dataset.validate()
    else:
        dataset.update(redis=self.redis)
    self.session.add(dataset)
    self.session.commit()
    return dataset.id
    
def rgenerate(dataset, telemetrykind, **kwargs):
    """Recursively generate using a celery chain."""
    c = chain(generate.si(dataset.id, prereq.id, **kwargs) for prereq in telemetrykind.rprerequisites[1:])
    return c