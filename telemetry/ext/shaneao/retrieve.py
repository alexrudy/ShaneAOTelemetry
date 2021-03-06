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
import h5py
import click

from telemetry.application import app
from celery.utils.log import get_task_logger

from .models import ShaneAODataFrame, ShaneAODataSequence, ShaneAOInfo
from telemetry.models import Dataset, Instrument, DatasetInfoBase
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
def generate_dataset(self, sequence_id, force=False):
    """Generate a dataset for this sequence."""
    sequence = self.session.query(ShaneAODataSequence).get(sequence_id)
    if sequence.filename is None:
        log.debug("No filename found for sequence {0:d}".format(sequence.id))
        return -1
    if sequence.dataset is None or force:
        # First, try to repair the match:
        sequence.dataset = self.session.query(Dataset).filter(Dataset.filename == sequence.filename).one_or_none()
    if sequence.dataset is None:
        # Regenerate dataset
        path_parts = os.path.abspath(sequence.filename).split(os.path.sep)
        instrument = Instrument.require(self.session, path_parts[-4])
        log.info("Opening {0}".format(sequence.filename))
        lock = self.redis.lock("ShaneAODataSequence{:d}".format(sequence.id), timeout=1000)
        with lock:
            with h5py.File(sequence.filename, mode='r') as f:
                sequence.dataset = Dataset.from_h5py_group(self.session, f['telemetry'])
                metadata = DatasetInfoBase.from_mapping(sequence.dataset, f['telemetry'].attrs, instrument=instrument.metadata_type)
                sequence.dataset.instrument = instrument
                sequence.dataset.update_h5py_group(self.session, f['telemetry'])
                sequence.dataset.validate()
                self.session.add(metadata)
    sequence.dataset.update(self.session)
    self.session.add(sequence.dataset)
    self.session.add(sequence)
    self.session.commit()
    self.session.refresh(sequence)
    return sequence.dataset.id

@app.celery.task(bind=True)
def map_sequence(self, dataset_id):
    """Generate sequence for a dataset and associate the sequence to that dataset."""
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
    return frame.id
    
@app.celery.task(bind=True)
def append_sequence(self, frame_id, root=None, force=False):
    """Append a frame to a sequence."""
    frame = self.session.query(ShaneAODataFrame).get(frame_id)
    sequence = frame.sequence
    root = root or os.path.join(app.config['TELEMETRY_ROOTDIRECTORY'], "ShaneAO")
    # Short out on a few common problems.
    if sequence is None:
        raise ValueError("Can't locate sequence to append frame.")
    if frame.included and not force:
        return frame.sequence.id
    
    with sequence.manager(self.redis, root, force=force) as manager:
        if manager.append_from_fits(frame.filename):
            log.info("{}:{}".format(os.path.basename(frame.filename), frame.created))
        frame.included = True
    self.session.add(frame)
    self.session.add(sequence)
    self.session.commit()
    return frame.sequence.id

@app.celery.task(bind=True)
def concatenate_sequence(self, seq_id, root=None, force=False):
    """Concatenate a telemetry sequence."""
    root = root or os.path.join(app.config['TELEMETRY_ROOTDIRECTORY'], "ShaneAO")
    sequence = self.session.query(ShaneAODataSequence).get(seq_id)
    with sequence.manager(self.redis, root, force=force) as manager:
        sequence.filename = manager.filename
        self.session.add(sequence)
        for frame in sequence.frames:
            if frame.included:
                continue
            if manager.append_from_fits(frame.filename):
                print("Concatenating from {:s}".format(os.path.basename(frame.filename)))
                log.info("{}:{}".format(os.path.basename(frame.filename), frame.created))
            frame.included = True
            self.session.add(frame)
        self.session.commit()
    return sequence.id

@app.celery.task
def unique(*ids):
    """Return only the unique ids."""
    return sorted(list(set(ids)))

def new_files_to_sequence(session, filepath, root=None, force=False):
    """Given a path to search for new files, yeild only tasks which apply to new files."""
    for filename in glob.iglob(os.path.join(filepath, '*.fits')):
        n = session.query(ShaneAODataFrame).filter(ShaneAODataFrame.filename == filename.decode('utf-8')).count()
        if n == 0:
            yield new_file_to_sequence(filename, root, force=force)
        elif n != 1:
            print("Multiple file matches found for {:s}".format(filename))

def new_file_to_sequence(filename, root, force=False):
    """Given a filename, return the chain required to ingest the new file."""
    return (load_single_file.s(filename, force=force) | match_sequence.s(force=force) | append_sequence.s(force=force))
    
def concatenate_all_sequences(session, root=".", force=False):
    """Concatenate all sequences."""
    query = session.query(ShaneAODataSequence).outerjoin(ShaneAODataSequence.frames)
    query = query.filter(~ShaneAODataFrame.included)
    return ((concatenate_sequence.si(sequence.id, root=root, force=force) | generate_dataset.s(force=force)) for sequence in query.all())

def generate_all_datasets(session, force=False):
    """Concatenate all sequences."""
    query = session.query(ShaneAODataSequence).filter(ShaneAODataSequence.dataset == None)
    return (generate_dataset.si(sequence.id, force=force) for sequence in query.all())

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

def rsync_telemetry(destination=".", date=None, extension='.fits'):
    """Launch an RSYNC of data."""
    if date is None:
        date = latest_remote_telemetry_date()
    if isinstance(date, (datetime.datetime, datetime.date)):
        date = date.strftime(DATEFMT)
    
    # Make the full destination path.
    destination = os.path.join(destination, 'raw', date)
    if not os.path.exists(destination):
        os.makedirs(destination)
    if not destination.endswith(os.path.sep):
        destination = destination + os.path.sep
    # Subprocess arguments for RSYNC
    telpath = os.path.join(app.config['SHANEAO_TELEMETRY_PATH'], "{date:s}", "*{extension:s}").format(
        date = date, extension = extension
    )
    
    args = ['rsync', '-avP',
            '{host:s}:{telpath:s}'.format(host=app.config['SHANEAO_TELEMETRY_HOST'], telpath=telpath),
            destination ]
    click.echo(" ".join(args))
    return subprocess.Popen(args)
    
