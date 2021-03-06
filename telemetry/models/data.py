# -*- coding: utf-8 -*-
"""
A single data set.
"""

import datetime
import os
import numbers
import contextlib
import collections
import pytz
import numpy as np
import six
import logging

from sqlalchemy import inspect
from sqlalchemy import Column, Table
from sqlalchemy import Integer, String, DateTime, Float, ForeignKey, Boolean, Date, Unicode
from sqlalchemy.orm import relationship, backref, validates, object_session
from sqlalchemy.sql import func
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.associationproxy import association_proxy

from astropy.io import fits
import h5py

from .base import Base
from .case import Telemetry, TelemetryKind

__all__ = ['Instrument', 'DatasetInfoBase', 'Dataset', 'Tag']

log = logging.getLogger(__name__)

class Instrument(Base):
    """An association object which matches an instrument to a dataset."""
    name = Column(Unicode)
    metadata_type = Column(String(30))
    
    @classmethod
    def require(cls, session, name):
        """Requrie an instrument."""
        instrument = session.query(cls).filter(cls.name == name).one_or_none()
        if not instrument:
            instrument = cls(name=name, metadata_type=name.lower())
            session.add(instrument)
        return instrument
        

class DatasetInfoBase(Base):
    """Instrument association base."""
    
    type = Column(String(30))
    
    _instrument_id = Column(Integer, ForeignKey("instrument.id"))
    instrument = relationship("Instrument")
    
    _dataset_id = Column(Integer, ForeignKey("dataset.id", ondelete='CASCADE'), unique=True)
    
    __mapper_args__ = {
        'polymorphic_identity' : 'base',
        'polymorphic_on' : type,
    }
    
    EXCLUDE = ("type",)
    
    def __repr__(self):
        """Represent the metadata."""
        return "{0}({1})".format(self.__class__.__name__, ", ".join("{0}={1}".format(k, v) for k,v in self.attributes().items()))
    
    @classmethod
    def from_mapping(cls, dataset, mapping, instrument='base'):
        """Create the metadata from a mapping."""
        
        # First, use the appropriate instrument class.
        mapper = inspect(cls).mapper
        cls = mapper.polymorphic_map[instrument].class_
        
        return cls._from_mapping(dataset, mapping)
        
    @classmethod
    def _from_mapping(cls, dataset, mapping):
        colnames = set(c.name for c in cls.__table__.columns)
        attrs = dict((k,mapping[k]) for k in mapping.keys() if k in colnames)
        for key in attrs:
            if isinstance(attrs[key], np.bool_):
                attrs[key] = bool(attrs[key])
        attrs['dataset'] = dataset
        return cls(**attrs)
    
    def check_attributes(self, mapping):
        """Check attributes."""
        colnames = set(c.name for c in self.__table__.columns)
        attrs = dict((k,mapping[k]) for k in mapping.keys() if k in colnames)
        mismatches = {}
        for key in attrs:
            if isinstance(attrs[key], np.bool_):
                attrs[key] = bool(attrs[key])
            if isinstance(getattr(self, key), numbers.Number):
                attrs[key] = float(attrs[key])
            if attrs[key] != getattr(self, key):
                mismatches[key] = (attrs[key], getattr(self, key))
        return mismatches
        
    
    def sequence_attributes(self):
        """The dictionary sequenece attributes."""
        return self.attributes()
    
    def match(self, session=None):
        """Match to a pair sequence"""
        cls = self.__class__
        session = session or object_session(self)
        match_query = session.query(cls).filter_by(**self.sequence_attributes())
        match_query = match_query.filter(cls.id != self.id, cls.loop != self.loop)
        matches = match_query.join(Dataset).order_by(func.abs(Dataset.sequence - self.dataset.sequence)).all()
        if not len(matches):
            return None
        closest = min(abs(s.dataset.sequence - self.dataset.sequence) for s in matches)
        matches = filter(lambda s : abs(s.dataset.sequence - self.dataset.sequence) <= closest, matches)
        return matches[0].dataset


dataset_tag_association_table = Table('dataset_tag_association', Base.metadata,
    Column('dataset_id', Integer, ForeignKey('dataset.id', ondelete="CASCADE")),
    Column('tag_id', Integer, ForeignKey('tag.id', ondelete="CASCADE"))
)

class Tag(Base):
    """A dataset tag"""
    text = Column(Unicode)
    datasets = relationship("Dataset", secondary=dataset_tag_association_table, back_populates="_tags")

class Dataset(Base):
    """A base class to share columns between dataset and sequence."""
    
    kinds = relationship("TelemetryKind", secondary="telemetry", viewonly=True)
    _tags = relationship("Tag", secondary=dataset_tag_association_table, back_populates="datasets")
    tags = association_proxy("_tags", "text")
    
    instrument_data = relationship("DatasetInfoBase", backref=backref("dataset", uselist=False), cascade="all", uselist=False)
    instrument_id = Column(Integer, ForeignKey("instrument.id"))
    instrument = relationship("Instrument", backref="datasets")
    filename = Column(Unicode, doc="Filename for the HDF5 data.")
    h5path = Column(String, doc="Path inside the HDF5 file to telemetry data.")
    sequence = Column(Integer, doc="Dataset sequence number.")
    created = Column(DateTime, doc="Creation datetime.")
    date = Column(Date, doc="Creation date (UT)")
    valid = Column(Boolean, doc="Is this dataset valid?", default=True)
    error_message = Column(Unicode, doc="Error message from opening this file.")
    
    # Data parameters which are universal.
    rate = Column(Float, doc="Sampling Rate")
    closed = Column(Boolean, doc="Was the loop closed")
    gain = Column(Float, doc="The gain for this dataset, as best as it can be identified for this instrument.")
    bleed = Column(Float, doc="The bleed for this dataset, as best as it can be identified for this instrument.")
    
    # Data parameters which are cached for querying.
    nsamples = Column(Integer)
    
    @validates('created')
    def validate_created(self, key, value):
        """Validate created."""
        if isinstance(value, numbers.Number):
            return datetime.datetime.fromtimestamp(value)
        elif value is None:
            value = datetime.datetime.now()
        return value
    
    @validates('date')
    def validate_date(self, key, value):
        """Validate the date."""
        if value is None and self.created is not None:
            timezone = pytz.timezone('US/Pacific')
            value = timezone.localize(self.created).astimezone(pytz.UTC).date()
        elif isinstance(value, numbers.Number):
            value = datetime.date.fromordinal(value)
        return value
        
    def validate(self):
        """Validate the HDF5 path and group."""
        if not os.path.exists(self.filename):
            return False
        with h5py.File(self.filename) as f:
            return self.h5path in f
            
    def set_date(self, value=None):
        """Set the date from the created date."""
        if value is None and self.created is not None:
            timezone = pytz.timezone('US/Pacific')
            value = timezone.localize(self.created).astimezone(pytz.UTC).date()
        self.date = value
    
    @contextlib.contextmanager
    def open(self, redis=None):
        """Open this H5PY file with a group."""
        if redis is not None:
            lock = redis.lock(self.filename)
            lock.acquire()
        try:
            with h5py.File(self.filename) as f:
                g = f[self.h5path]
                yield g
                session = object_session(self)
                if session is not None:
                    self.update_h5py_group(session, g)
        finally:
            if redis is not None:
                lock.release()
    
    def _validate_h5py_item_visitor(self, name, item):
        """A visitor to validate problems in datasets."""
        if isinstance(item, h5py.Dataset):
            if not np.isfinite(item).all():
                raise ValueError("{0} contains non-finite data.".format(item))
    
    def update_h5py_group(self, session, g, verify=False):
        """Update database to match the HDF5 group"""
        if g.name != self.h5path:
            g = g.file[self.h5path]
            
        mismatches = self.instrument_data.check_attributes(g.attrs)
        for k, (v1, v2) in mismatches.items():
            log.warning("Mismatches for {0}: {1}={2}->{3}".format(self, k, v1, v2))
            log.info("Mismatches for {0}: {1}={2}->{3}".format(self, k, type(v1), type(v2)))
        checked_paths = set()
        to_check_paths = [kind.h5path for kind in session.query(TelemetryKind).all()]
        keys = collections.deque(to_check_paths)
        keys.extend(g.keys())
        
        for key in g.keys():
            if isinstance(g[key], h5py.Dataset):
                self.nsamples = max(self.nsamples or 0, g[key].shape[-1])
        
        while len(keys):
            key = keys.popleft()
            kind = session.query(TelemetryKind).filter(TelemetryKind.h5path == key).one_or_none()
            if kind is not None:
                if (kind.h5path in g) and (kind.h5path not in self.telemetry):
                    self.telemetry[kind.h5path] = Telemetry(kind=kind, dataset=self)
            elif isinstance(g.get(key, None), h5py.Group):
                sg = g[key]
                if sg.keys() == ["data", "mask"]:
                    kind = TelemetryKind.require(session, key, key)
                    self.telemetry[kind.h5path] = Telemetry(kind=kind, dataset=self)
                else:
                    keys.extend("/".join([key, subkey]) for subkey in g[key].keys())
            else:
                kind = TelemetryKind.require(session, key, key)
                self.telemetry[kind.h5path] = Telemetry(kind=kind, dataset=self)
                
        
        for telemetry in list(self.telemetry.values()):
            if telemetry.kind.h5path not in g:
                del self.telemetry[telemetry.kind.h5path]
        
        if verify:
            g.visititems(self._validate_h5py_item_visitor)
            if self.nsamples == 0:
                raise ValueError("Dataset has no samples.")
        
        return
        
    def update(self, session=None, verify=False, redis=None):
        """Update this HDF5 object."""
        with self.open(redis=redis) as g:
            if session is None:
                session = object_session(self)
            if session is not None:
                self.update_h5py_group(session, g, verify=verify)
    
    def validate(self):
        """Validate this entire dataset."""
        try:
            self.update(verify=True)
        except Exception as e:
            self.error_message = six.text_type(repr(e))
            self.valid = False
        else:
            self.valid = True
            self.error_message = None
    
    @classmethod
    def from_h5py_group(cls, session, g):
        """Create ths object from an HDF5 file."""
        colnames = set(c.name for c in cls.__table__.columns)
        attrs = dict((k,g.attrs[k]) for k in g.attrs.keys() if k in colnames)
        attrs['h5path'] = g.name
        
        filename = g.file.filename
        if not isinstance(filename, six.text_type):
            filename = filename.decode('utf-8')
        attrs['filename'] = filename
        attrs['created'] = datetime.datetime.now()
        for key in attrs:
            if isinstance(attrs[key], np.bool_):
                attrs[key] = bool(attrs[key])
        
        dataset = cls(**attrs)
        dataset.set_date()
        return dataset
    
    def __repr__(self):
        """Sensible representation."""
        try:
            return "{0}(sequence={sequence:d}, date={date:%Y-%m-%d})".format(self.__class__.__name__, **self.attributes())
        except ValueError:
            return "{0}(id={1})".format(self.__class__.__name__, self.id)
        
    def title(self):
        """A matplotlib-suitable title string."""
        attrs = self.attributes()
        attrs['gtext'] = self.gaintext
        try:
            return "{0} {sequence:d} on {date:%Y-%m-%d} ({gtext:s}, b={bleed:.2f}) @{rate:.0f}Hz".format(self.__class__.__name__, **attrs)
        except ValueError:
            return "{0} id={1}".format(self.__class__.__name__, self.id)
        
    
    @property
    def path(self):
        """Path root for this dataset."""
        return os.path.normpath(os.path.join(os.path.dirname(self.filename), ".."))
        
    @property
    def gaintext(self):
        """A textual description of the gain."""
        return "g={0:.3f}".format(self.gain) if self.closed else "open"
        




        