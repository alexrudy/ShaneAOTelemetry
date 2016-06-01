# -*- coding: utf-8 -*-
"""
Modeling figures on the filesystem.
"""
from sqlalchemy import Column, Table
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref, validates

from .base import File

__all__ = ['Figure']

class Figure(File):
    """A figure is a single image file."""
    
    telemetry_id = Column(Integer, ForeignKey("telemetry.id"))
    telemetry = relationship("Telemetry", backref="figures")
    
    @property
    def dataset(self):
        """The dataset"""
        return self.telemetry.dataset
        
    @property
    def kind(self):
        """The telemetry kind."""
        return self.telemetry.kind
    
    figure_type = Column(String, doc="The type of this figure.")
    
    def generate_filepath(self, folder='figures'):
        """Generate the filepath for this figure."""
        path = os.path.join(self.dataset.path, folder, 
            "s{0:04d}".format(self.dataset.sequence),
            self.kind.h5path.replace("/", "."),
            "{0:s}.s{1:04d}.{2:s}.{3:s}".format(self.figure_type, self.sequence, 
            self.kind.h5path.replace("/", "."), ext))
        self.filepath = path
        return self.filepath
    
    