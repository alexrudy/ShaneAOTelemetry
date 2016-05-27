# -*- coding: utf-8 -*-

from sqlalchemy import Column, Table
from sqlalchemy import Integer, String, DateTime, Float, ForeignKey, Boolean, Date, Unicode
from sqlalchemy.ext.hybrid import hybrid_property 
from sqlalchemy.orm import relationship, backref
from telemetry.models.data import DatasetInfoBase
from telemetry.models.base import Base

from .header import parse_values_from_header
from .sequencer import TelemetrySequence

from astropy.io import fits

import six
import json
import time
import datetime

__all__ = ['ShaneAOMetadata', 'ShaneAODataFrame']

class ShaneAODataSequence(Base):
    """A shaneAO sequence of data frame items."""
    dataset_id = Column(Integer, ForeignKey('dataset.id', ondelete='SET NULL'))
    dataset = relationship('Dataset')
    starttime = Column(DateTime, doc="Start of sequence time.")
    stoptime = Column(DateTime, doc="End of sequence time.")
    sequence_json = Column(Unicode, doc="Sequence attributes, in JSON format.")
    filename = Column(Unicode, doc="Filename from the sequence manager.")
    
    @property
    def sequence_attributes(self):
        """Sequence attributes as a dictionary."""
        return json.loads(self.sequence_json)
        
    def manager(self):
        """The sizes of various components."""
        attrs = self.sequence_attributes
        if len(sequence.frames):
            attrs['created'] = time.mktime(sequence.frames[0].created.timetuple())
        return TelemetrySequence(attrs)
        
    def add(self, frame):
        """Expand timeframes for the sequence."""
        frame.sequence = self
        self.starttime = min([self.starttime, frame.created])
        self.stoptime = max([self.stoptime, frame.created])
        
    def __repr__(self):
        """Represent the sequence."""
        return "{0:s}({1:s})".format(
            self.__class__.__name__,
            ", ".join(["{0:s}={1!r}".format(k, v) for k, v in self.attributes(exclude=['sequence_json', 'dataset_id', 'starttime', 'stoptime'], include=['dataset']).items() ]),
        )

class ShaneAODataFrame(Base):
    """A single frame from a ShaneAO telemetry dump"""
    
    valid = Column(Boolean, default=True, doc="Is this frame valid?")
    included = Column(Boolean, default=False, doc="Is this included.")
    onSky = Column(Boolean, default=False, doc="Was this frame taken OnSky?")
    sequence_json = Column(Unicode, doc="Sequence attributes, in JSON format.")
    header = Column(Unicode, doc="Full header, in JSON format.")
    filename = Column(Unicode, doc="Full path to FITS file.")
    length = Column(Integer, doc="Length of the telemetry dump.")
    created = Column(DateTime, doc="Creation datetime.")
    sequence_id = Column(Integer, ForeignKey(ShaneAODataSequence.id, ondelete='SET NULL'))
    sequence = relationship(ShaneAODataSequence, backref=backref("frames", order_by=created))
    
    @property
    def sequence_attributes(self):
        """Sequence attributes as a dictionary."""
        return json.loads(self.sequence_json)
    
    def refresh_attributes(self):
        """Refresh the JSON attributes here."""
        self.sequence_json, self.created = self.json_from_fits(fits.getheader(self.filename))
        
        
    @classmethod
    def json_from_fits(cls, header):
        """Get the JSON string from a fits filename."""
        sa = parse_values_from_header(header)
        created = sa.pop('created', None)
        for k,v in sa.items():
            if isinstance(v, (datetime.datetime,)):
                sa[k] = time.mktime(v.timetuple())
            elif isinstance(v, (datetime.date,)):
                sa[k] = v.toordinal()
            elif isinstance(v, float):
                sa[k] = "{:.5f}".format(v)
        sa.setdefault('refCent_filename', sa.pop('refCent_file', ''))
        return six.text_type(json.dumps(sa, sort_keys=True)), created
    
    @classmethod
    def from_fits(cls, filename):
        """From a FITS file."""
        header = fits.getheader(filename)
        kwargs = {}
        
        kwargs['filename'] = filename
        kwargs['header'] = json.dumps(header.items())
        kwargs['length'] = header['NAXIS2'] - 1
        kwargs['sequence_json'], kwargs['created'] = cls.json_from_fits(header)
        return cls(**kwargs)
    

class ShaneAOInfo(DatasetInfoBase):
    """An object containing the ShaneAO Info."""
    
    id = Column(Integer, ForeignKey(DatasetInfoBase.id, ondelete="CASCADE"), primary_key=True)
    
    __mapper_args__ = {
        'polymorphic_identity' : 'shaneao',
    }
    
    # Additional ShaneAO paramaters
    valid = Column(Boolean, default=True, doc="A flag to mark a header as unreliable.")
    onSky = Column(Boolean, default=False, doc="Is the data from an on-sky source.")
    reconstructor = Column(Unicode, default=u"VMM")
    
    # Telescope Position
    _alt = Column(Float, default=0, doc="Altitude.")
    _az = Column(Float, default=0, doc="Azimuth.")
    
    # Source position
    _ra = Column(Float, default=0, doc="Right Ascension.")
    _dec = Column(Float, default=0, doc="Declination.")
    
    # ShaneAO Operational parameters
    mode = Column(String)
    substate = Column(String)
    rtc = Column(String, doc='RTC Library in use.', default="rtc2")
    rtc_so = Column(String, doc="Filename of the RTC library.", default="rtc2.so")
    handler = Column(String, doc="Handler for the WFS camera", default="c_recon")
    
    wfs_rate = Column(Float)
    wfs_centroid = Column(String)
    wfs_camera_state = Column(String)
    
    gain = Column(Float)
    
    alpha = Column(Float)
    loop = Column(String)
    control_matrix = Column(String, doc="Control matrix name.")
    ngs_matrix = Column(String, doc="NGS Control Matrix name.")
    reference_centroids = Column(String)
    frozen = Column(Boolean)
    
    hybrid_mode = Column(String)
    hybrid_matrix = Column(String, doc="Hybrid matrix name.")
    hybrid_bleed = Column(Float, doc="Hybrid mode bleed.")
    
    tweeter_enable = Column(Boolean)
    tweeter_gain = Column(Float)
    tweeter_bleed = Column(Float)
    tweeter_check = Column(Boolean)
    
    woofer_rate = Column(Float)
    woofer_gain = Column(Float)
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
    
    def __init__(self, **kwargs):
        kwargs.setdefault("woofer_gain", kwargs.get("gain"))
        kwargs.setdefault("tweeter_gain", kwargs.get("gain"))
        
        if 'hybrid_matrix' in kwargs:
            kwargs['reconstructor'] = "SMM"
        if 'hybrid_bleed' in kwargs:
            kwargs['reconstructor'] = "SMM-ID"
        
        super(ShaneAOInfo, self).__init__(**kwargs)
        
    @classmethod
    def _from_mapping(cls, dataset, mapping):
        """Set the dataset attributes appropriately."""
        obj = super(ShaneAOInfo, cls)._from_mapping(dataset, mapping)
        dataset.rate = obj.wfs_rate
        dataset.gain = obj.tweeter_gain
        dataset.bleed = obj.tweeter_bleed
        dataset.closed = obj.loop.lower() == "closed"
        return obj
    
    @hybrid_property
    def rate(self):
        """Primary system rate."""
        return self.wfs_rate
    
    SEQUENCE_EXCLUDES = ["id", "loop", "gain", "reference_centroids", "alpha", "woofer_bleed",
        "woofer_gain", "tweeter_bleed", "tweeter_gain", "tt_rgain", "tt_centroid",
        "uplink_loop", "uplink_angle", "uplink_bleed", "uplink_gain", "uplink_enabled"]
    
    def sequence_attributes(self):
        """A dictionary of only the attributes which are relevant to sequencing."""
        attrs = self.attributes()
        for key in self.SEQUENCE_EXCLUDES:
            attrs.pop(key, None)
        return attrs
    

