# -*- coding: utf-8 -*-
"""
Retrieve data from Mt. Hamilton for ShaneAO
"""
import datetime
import time
import os
import subprocess
import glob
import json
import numpy as np
import celery

from telemetry.application import app
from celery.utils.log import get_task_logger

from .models import ShaneAODataFrame, ShaneAODataSequence, ShaneAOInfo
from telemetry.models import Dataset
from telemetry import tasks

log = get_task_logger(__name__)

def dataset_get_sequence_attributes(mapping):
    """Get the equivalent of sequence attributes from a dataset."""
    colnames = set(c.name for c in ShaneAOInfo.__table__.columns)
    attrs = dict((k,mapping[k]) for k in mapping.keys())
    for key in attrs:
        if isinstance(attrs[key], np.bool_):
            attrs[key] = bool(attrs[key])
        elif isinstance(attrs[key], float):
            attrs[key] = "{:.5f}".format(attrs[key])
    attrs.pop('unreal', None)
    attrs.pop('created', None)
    attrs.pop('length', None)
    attrs.pop('sequence', None)
    return attrs

@app.celery.task(bind=True)
def load_single_file(self, filename, force=False):
    """Load a single fits file as a ShaneAO frame."""
    frame = self.session.query(ShaneAODataFrame).filter(ShaneAODataFrame.filename==filename).one_or_none()
    if not frame:
        frame = ShaneAODataFrame.from_fits(filename)
    elif force:
        frame.refresh_attributes()
    self.session.add(frame)
    self.session.commit()
    self.session.refresh(frame)
    return frame.id

@app.celery.task(bind=True)
def load(self, root, date="*", force=False):
    """Load any new datasets from Mt Hamilton."""
    for filename in glob.iglob(os.path.join(root, "raw", date, "*.fits")):
        frame = self.session.query(ShaneAODataFrame).filter(ShaneAODataFrame.filename==filename).one_or_none()
        if not frame:
            frame = ShaneAODataFrame.from_fits(filename)
        elif force:
            frame.refresh_attributes()
        self.session.add(frame)
    self.session.commit()

@app.celery.task(bind=True)
def map_sequence(self, dataset_id):
    """docstring for map_sequence"""
    dataset = self.session.query(Dataset).get(dataset_id)
    sequence = self.session.query(ShaneAODataSequence).filter_by(dataset_id=dataset_id).one_or_none()
    if sequence is None:
        with dataset.open() as g:
            attrs = dataset_get_sequence_attributes(g.attrs)
        sequence = ShaneAODataSequence(dataset=dataset, sequence_json=json.dumps(attrs, sort_keys=True))
    else:
        with dataset.open() as g:
            attrs = dataset_get_sequence_attributes(g.attrs)
        sequence.sequence_json = json.dumps(attrs, sort_keys=True)
    self.session.add(sequence)
    self.session.commit()
    
@app.celery.task(bind=True)
def match_sequence(self, frame_id, maxsep=15, force=False):
    """Check a frame, find a matching dataset, append frame to dataset."""
    frame = self.session.query(ShaneAODataFrame).get(frame_id)
    if (frame.sequence is None) or force:
        q = self.session.query(ShaneAODataSequence)
        q = q.filter(ShaneAODataSequence.sequence_json==frame.sequence_json)
        log.info("Sequence time limits: {0}".format(datetime.timedelta(seconds=maxsep*60)))
        q = q.filter(ShaneAODataSequence.starttime - frame.created < datetime.timedelta(seconds=maxsep*60))
        q = q.filter(ShaneAODataSequence.stoptime - frame.created > -datetime.timedelta(seconds=maxsep*60))
        if q.count():
            sequence = q.first()
        else:
            sequence = None
        if not sequence:
            sequence = ShaneAODataSequence(sequence_json=frame.sequence_json,
                starttime=frame.created, stoptime=frame.created)
            self.session.add(sequence)
        sequence.add(frame)
        
    self.session.commit()
    self.session.refresh(frame)
    return frame.sequence.id
    
@app.celery.task(bind=True)
def concatenate_sequence(self, seq_id, root=".", force=False):
    """Concatenate a telemetry sequence."""
    sequence = self.session.query(ShaneAODataSequence).get(seq_id)
    manager = sequence.manager()
    base = os.path.join(root, sequence.frames[0].created.date().strftime("%Y-%m-%d"), "data")
    try:
        manager.setup(sequence.id, base, mode="w" if force else "a")
    except Exception as e:
        log.error(e)
        manager.close()
        manager.setup(sequence.id, base, mode="w")
    sequence.filename = manager.filename
    self.session.add(sequence)
    for frame in sequence.frames:
        if manager.append_from_fits(frame.filename):
            log.info("{}:{}".format(os.path.basename(frame.filename), frame.created))
        frame.included = True
        self.session.add(frame)
    self.session.commit()
    return manager.filename

def new_file_to_sequence(filename, root, force=False):
    """Given a filename, return the chain required to ingest the new file."""
    return (load_single_file.s(filename, force=force) | match_sequence.s(force=force))
    
def concatenate_all_sequences(session, root=".", force=False):
    """Concatenate all sequences."""
    query = session.query(ShaneAODataSequence).outerjoin(ShaneAODataSequence.frames)
    query = query.filter(~ShaneAODataFrame.included)
    return (concatenate_sequence.si(sequence.id, root=root, force=force) for sequence in query.all())

DATEFMT = "%Y-%m-%d"

def list_remote_telemetry_directory():
    """List the remote telemetry directory"""
    try:
        args = ['ssh', app.config['SHANEAO_TELEMETRY_HOST'], 'ls telemetry/']
        response = subprocess.check_output(args)
    except subprocess.CalledProcessError as e:
        print("CRITICAL ERROR: {0}".format(e.output))
        raise
    return response.splitlines()
    
def latest_remote_telemetry_date():
    """Get the latest telemetry directory"""
    dates = []
    for d in list_remote_telemetry_directory():
        try:
            dates.append(datetime.datetime.strptime(d, DATEFMT))
        except ValueError:
            pass
    dates.sort()
    return dates[-1]

def rsync_telemetry(destination=".", date=None):
    """Launch an RSYNC of data."""
    if date is None:
        date = latest_remote_telemetry_date()
    if isinstance(date, (datetime.datetime, datetime.date)):
        date = date.strftime(DATEFMT)
    
    # Make the full destination path.
    destination = os.path.join(destination, 'ShaneAO', 'raw', date)
    if not os.path.exists(destination):
        os.makedirs(destination)
    
    # Subprocess arguments for RSYNC
    args = ['rsync', '-avP',
        '{host:s}:telemetry/{date:s}/*.fits'.format(host=app.config['SHANEAO_TELEMETRY_HOST'], date=date),
        destination ]
    print(" ".join(args))
    return subprocess.Popen(args)
    
