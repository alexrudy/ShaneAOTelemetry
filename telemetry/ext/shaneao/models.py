# -*- coding: utf-8 -*-

from sqlalchemy import Column, Table
from sqlalchemy import Integer, String, DateTime, Float, ForeignKey, Boolean, Date, Unicode
from sqlalchemy.ext.hybrid import hybrid_property 

from telemetry.models.data import DatasetMetadataBase

class ShaneAOMetadata(DatasetMetadataBase):
    """An object containing the ShaneAO Metadata."""
    
    id = Column(Integer, ForeignKey(DatasetMetadataBase.id))
    
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
        super(ShaneAOMetadata, self).__init__(**kwargs)
        
    
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