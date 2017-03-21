# -*- coding: utf-8 -*-
from sqlalchemy import Column, Table
from sqlalchemy import Integer, String, DateTime, Float, ForeignKey, Boolean, Date, Unicode
from sqlalchemy.ext.hybrid import hybrid_property 
from telemetry.models.data import DatasetInfoBase

from .attrs import parse_values_from_header

from astropy.io import fits

import os
import six
import json
import time
import logging
import datetime
import collections
import contextlib

log = logging.getLogger(__name__)

class ShadyAOInfo(DatasetInfoBase):
    """An object containing the ShaneAO Info."""
    
    id = Column(Integer, ForeignKey(DatasetInfoBase.id, ondelete="CASCADE"), primary_key=True)
    
    __mapper_args__ = {
        'polymorphic_identity' : 'shadyao',
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
        
    wfs_rate = Column(Float)
    wfs_centroid = Column(String)
    wfs_cent_reg = Column(Float)
    wfs_camera_state = Column(String)
    
    gain = Column(Float)
    
    alpha = Column(Float)
    loop = Column(String)
    control_matrix = Column(String, doc="Control matrix name.")
    hybird_matrix = Column(String, doc="Hybrid matrix name.")
    reference_centroids = Column(String)
    
    hybrid_matrix = Column(String, doc="Hybrid matrix name.")
    
    tweeter_enable = Column(Boolean)
    tweeter_gain = Column(Float)
    tweeter_bleed = Column(Float)
    tweeter_lower_lim = Column(Float)
    tweeter_upper_lim = Column(Float)
    tweeter_na = Column(Integer)
    
    woofer_rate = Column(Float)
    woofer_gain = Column(Float)
    woofer_enable = Column(Boolean)
    woofer_bleed = Column(Float)
    
    tt_rate = Column(Float)
    tt_centroid = Column(String)
    tt_camera_state = Column(String)
    
    def __init__(self, **kwargs):
        kwargs.setdefault("woofer_gain", kwargs.get("gain"))
        kwargs.setdefault("tweeter_gain", kwargs.get("gain"))
        super(ShadyAOInfo, self).__init__(**kwargs)
        
    @classmethod
    def _from_mapping(cls, dataset, mapping):
        """Set the dataset attributes appropriately."""
        parsed_mapping = parse_values_from_header(mapping)
        print(dict(mapping))
        print(parsed_mapping)
        obj = super(ShadyAOInfo, cls)._from_mapping(dataset, parsed_mapping)
        dataset.rate = obj.wfs_rate
        dataset.gain = obj.tweeter_gain
        dataset.bleed = obj.tweeter_bleed
        if obj.loop is not None:
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
