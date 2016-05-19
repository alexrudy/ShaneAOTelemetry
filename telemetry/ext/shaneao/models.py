# -*- coding: utf-8 -*-

from sqlalchemy import Column, Table
from sqlalchemy import Integer, String, DateTime, Float, ForeignKey, Boolean, Date, Unicode
from sqlalchemy.ext.hybrid import hybrid_property 

from telemetry.models.data import DatasetInfoBase
from telemetry.models.base import Base

__all__ = ['ShaneAOMetadata']

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
            del attrs[key]
        return attrs
    

