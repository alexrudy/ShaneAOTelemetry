# -*- coding: utf-8 -*-
"""
A single data set.
"""

import datetime
import os
import numbers
import contextlib
import pytz
import numpy as np
import six

from sqlalchemy import inspect
from sqlalchemy import Column, Table
from sqlalchemy import Integer, String, DateTime, Float, ForeignKey, Boolean, Date, Unicode
from sqlalchemy.orm import relationship, backref, validates, object_session
from sqlalchemy.sql import func
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.declarative import declared_attr

from astropy.io import fits
import h5py

from .base import Base, FileBase, DataAttribute
from .. import makedirs
from ..algorithms.coefficients import get_cm_projector, get_matrix

def _parse_values_from_header(filename):
    """Parse argument values from a header file."""
    args = {}
    header = fits.getheader(filename)
    
    _HEADER_VALUES = [
        ('NAXIS1', 'n_elements', int),
        ('SYSTEM', 'system', str),
        ('HEARTBEA', 'tweeter_heartbeat', bool),
        ('RTC_STAT', 'recon_enable', bool),
        ('RATE', 'wfs_rate', float),
        ('GAIN', 'gain', float),
        ('CENT', 'wfs_centroid', str),
        ('WOOFER_B', 'woofer_bleed', float),
        ('TWEETER_', 'tweeter_bleed', float),
        ('ALPHA', 'alpha', float),
        ('MODE', 'mode', str),
        ('SUBSTATE', 'substate', str),
        ('LOOP', 'loop', str),
        ('CONTROLM', 'control_matrix', str),
        ('REFCENT_', 'reference_centroids', str),
        ('TTRATE', 'tt_rate', float),
        ('TTCENT', 'tt_centroid', str),
        ('WOOFER', 'woofer_enable', lambda s : s == "on"),
        ('MEMS', 'tweeter_enable', lambda s : s == "on"),
        ('MEMS_OK', 'tweeter_check', bool),
        ('CAMERA', 'wfs_camera_state', str),
        ('WRATE', 'woofer_rate', float),
        ('TTCAMERA', 'tt_camera_state', str),
        ('TT_RGAIN', 'tt_rgain', float),
        ('FROZEN', 'frozen', bool),
        ('OFFLOADI', 'offload_enable', bool),
        ('UPLINK_L', 'uplink_loop', str),
        ('UPLINK_A', 'uplink_angle', float),
        ('UPLINK_B', 'uplink_bleed', float),
        ('UPLINK_G', 'uplink_gain', float),
        ('UPLINK_E', 'uplink_enabled', bool)
    ]
    
    for key, name, kind in _HEADER_VALUES:
        try:
            args[name] = kind(header[key])
        except ValueError:
            if header[key] != 'unknown':
                print("Can't parse {0}={1!r} as {2}".format(key, header[key], kind.__name__))
    
    datestring = header['DATE'] + "T" + header['TIME']
    args['created'] = datetime.datetime.strptime(datestring, '%Y-%m-%dT%H%M%S')
    args['date'] = args['created'].date()
    return args
    

class Telemetry(Base):
    """An association object with methods for telemetry."""
    _telemetry_kind_id = Column(Integer, ForeignKey('telemetrykind.id'))
    kind = relationship("TelemetryKind")
    
    _dataset_id = Column(Integer, ForeignKey('dataset.id'))
    dataset = relationship("Dataset", back_populates="telemetry")
    
    @contextlib.contextmanager
    def open(self):
        """Open the dataset, as a context manager."""
        with self.dataset.open() as g:
            try:
                yield g[self.kind.h5path]
            except KeyError as e:
                print("Error opening {0} from {1} in {2}".format(self.kind.h5path, g.name, repr(self.dataset)))
                raise
            
    def read(self):
        """Read the dataset."""
        with self.open() as d:
            return d[...]
            
    def remove(self):
        """Remove telemetry"""
        with self.dataset.open() as g:
            g.pop(self.kind.h5path, None)
        
    def __repr__(self):
        """A telemetry data item."""
        return "<{0}({1}) kind={2} h5path={3} from Dataset {4:d}>".format(self.__class__.__name__,
            self.kind.__class__.__name__, self.kind.kind, 
            "/".join([self.dataset.h5path,self.kind.h5path]),
            self.dataset.sequence)

class TelemetryKind(Base):
    """A dataset in an HDF5 file, representing a specific type of telemetry."""
    
    _kind = Column(String)
    name = Column(String)
    h5path = Column(String, unique=True)
    
    __mapper_args__ = {
            'polymorphic_identity': 'base',
            'polymorphic_on':'_kind',
        }
    
    def __repr__(self):
        """Represent this object"""
        return "<{0} name={1} h5path={2}>".format(self.__class__.__name__, self.name, 
            self.h5path)
    
    @property
    def kind(self):
        """Telemetry base kind."""
        return self.name
    
    @classmethod
    def create(cls, session, name, h5path=None):
        """Create a telemetry kind from a session"""
        if h5path is None:
            h5path = name
        kind = session.query(cls).filter(cls.name == name).one_or_none()
        if kind is None:
            session.add(cls(name=name, h5path=h5path))
            kind = session.query(cls).filter(cls.name == opt.kind).one()
        return kind
    
    @validates('h5path')
    def validate_name(self, key, value):
        """Validate name."""
        if self._kind is None or self._kind == "base":
            mapper = inspect(self).mapper
            if value in mapper.polymorphic_map:
                self._kind = value
            else:
                self._kind = 'base'
        return value
    

class Dataset(Base):
    """A base class to share columns between dataset and sequence."""
    
    telemetry = relationship("Telemetry", back_populates="dataset", cascade="all, delete-orphan",
        collection_class=attribute_mapped_collection('kind.h5path'))
    kinds = relationship("TelemetryKind", secondary='telemetry')
    
    filename = Column(Unicode)
    h5path = Column(String)
    sequence = Column(Integer)
    created = Column(DateTime)
    date = Column(Date)
    
    # ShaneAO Operational parameters
    valid = Column(Boolean, default=True) # A flag to mark a header as unreliable.
    
    mode = Column(String)
    substate = Column(String)
    
    wfs_rate = Column(Float)
    wfs_centroid = Column(String)
    wfs_camera_state = Column(String)
    
    gain = Column(Float)
    
    alpha = Column(Float)
    loop = Column(String)
    control_matrix = Column(String)
    reference_centroids = Column(String)
    frozen = Column(Boolean)
    
    tweeter_enable = Column(Boolean)
    tweeter_bleed = Column(Float)
    tweeter_check = Column(Boolean)
    
    woofer_rate = Column(Float)
    woofer_enable = Column(Boolean)
    woofer_bleed = Column(Float)
    offload_enable = Column(Boolean)
    
    tt_rgain = Column(Float)
    tt_rate = Column(Float)
    tt_centroid = Column(String)
    tt_camera_state = Column(String)
    
    uplink_loop = Column(String)
    uplink_angle = Column(Float)
    uplink_bleed = Column(Float)
    uplink_gain = Column(Float)
    uplink_enabled = Column(Boolean)
    
    @validates('created')
    def validate_created(self, key, value):
        """Validate created."""
        if isinstance(value, numbers.Number):
            return datetime.datetime.fromtimestamp(value)
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
    def open(self):
        """Open this H5PY file with a group."""
        with h5py.File(self.filename) as f:
            g = f[self.h5path]
            yield g
            session = object_session(self)
            if session is not None:
                self.update_h5py_group(session, g)
    
    def update_h5py_group(self, session, g):
        """Update database to match the HDF5 group"""
        if g.name != self.h5path:
            g = g.file[self.h5path]
            
        kinds = session.query(TelemetryKind).all()
        for kind in kinds:
            if kind.h5path in g and kind.name not in self.telemetry:
                self.telemetry[kind.h5path] = Telemetry(kind=kind, dataset=self)
        
        # for key in g.keys():
        #     if hasattr(g[key], 'shape'):
        #         kind = session.query(TelemetryKind).filter(TelemetryKind.h5path == key).one_or_none()
        #         if kind is None:
        #             kind = TelemetryKind(name = key, h5path = key)
        #             session.add(kind)
        #         if kind.name not in self.telemetry:
        #             self.telemetry[kind.name] = Telemetry(kind=kind, dataset=self)
        
        for telemetry in list(self.telemetry.values()):
            if telemetry.kind.h5path not in g:
                del self.telemetry[telemetry.kind.h5path]
        return
        
    def update(self, session=None):
        """Update this HDF5 object."""
        with self.open() as g:
            if session is not None:
                self.update_h5py_group(session, g)
    
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
        attrs['date'] = None
        dataset = cls(**attrs)
        dataset.set_date()
        dataset.update_h5py_group(session, g)
        return dataset
    
    def __repr__(self):
        """Sensible representation."""
        return "<{0} {sequence:d} from {date:%Y-%m-%d} mode={mode:s} loop={loop:s} gain={gain:.2f}>".format(self.__class__.__name__, **self.attributes())
    
    @property
    def path(self):
        """Path root for this dataset."""
        return os.path.normpath(os.path.join(os.path.dirname(self.filename), ".."))
        
    def sequence_attributes(self):
        """The dictionary sequenece attributes."""
        attrs = self.attributes()
        keys = set()
        keys |= set("filename h5path sequence created date valid id".split())
        keys |= set("loop gain reference_centroids alpha woofer_bleed tweeter_bleed".split())
        keys |= set("tt_rgain tt_centroid".split())
        keys |= set("uplink_loop uplink_angle uplink_bleed uplink_gain uplink_enabled".split())
        for key in keys:
            del attrs[key]
        return attrs
    
    def match(self):
        """Match to a pair sequence"""
        cls = self.__class__
        match_query = object_session(self).query(cls).filter_by(**self.sequence_attributes()).filter(cls.id != self.id).filter(cls.loop != self.loop)
        matches = match_query.order_by(func.abs(cls.sequence - self.sequence)).all()
        if not len(matches):
            return None
        closest = min(abs(s.sequence - self.sequence) for s in matches)
        matches = filter(lambda s : abs(s.sequence - self.sequence) <= closest, matches)
        return matches[0]



        