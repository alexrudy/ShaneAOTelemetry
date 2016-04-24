# -*- coding: utf-8 -*-
"""
Data generators.
"""
import abc
from .data import TelemetryKind
from telemetry.algorithms.coefficients import get_cm_projector, get_matrix
import numpy as np

__all__ = ['TelemetryGenerator', 'SlopeVectorX', 'SlopeVectorY', 'HCoefficients', 'HEigenvalues', 'PseudoPhase']

class TelemetryGenerator(TelemetryKind):
    
    __tablename__ = 'telemetrykind'
    
    @abc.abstractmethod
    def generate(self, dataset):
        """Generate data for a dataset."""

class SlopeVector(TelemetryGenerator):
    """Slope vector telemetry, splits slopes if necessary."""
    
    _NSLOPES = {
        16 : 144
    }
    
    def generate(self, dataset):
        """Generate data for a dataset."""
        s = dataset.telemetry['slopes'].read()
        n_across = int(dataset.mode.split('x',1)[0])
        ns = self._NSLOPES[n_across]
        idx = {'sx':0,'sy':1}[self.name]
        with dataset.open() as g:
            g.create_dataset(self.h5path, data=s[idx*ns:(idx+1)*ns,:])
    
class SlopeVectorX(SlopeVector):
    """docstring for SlopeVectorX"""
    
    __mapper_args__ = {
            'polymorphic_identity':'sx',
        }

class SlopeVectorY(SlopeVector):
    """docstring for SlopeVectorX"""
    
    __mapper_args__ = {
            'polymorphic_identity':'sy',
        }
    

class MatrixTransform(TelemetryGenerator):
    """A generic Matrix transformer."""
    MATRIX = None
    SOURCE = 'slopes'
    
    def generate(self, dataset):
        """Generate data for a dataset."""
        s = dataset.telemetry[self.SOURCE].read()
        s = np.matrix(s)
        s.shape = (s.shape[0], s.shape[1], 1)

        vm = get_matrix(self.MATRIX)
        coeffs = vm * s
        coeffs = coeffs.view(np.ndarray)
        with dataset.open() as g:
            g.create_dataset(self.h5path, data=coeffs)

class HCoefficients(MatrixTransform):
    """Coefficients of the H matrix, generated from slopes."""
    
    __mapper_args__ = {
            'polymorphic_identity':'hcoefficients',
        }
    
    MATRIX = "H_d"
    
class PseudoPhase(MatrixTransform):
    """Pseudophase, generated from WFS slopes."""
    
    __mapper_args__ = {
            'polymorphic_identity':'pseudophase',
        }
        
    MATRIX = "L"
    


class FourierCoefficients(MatrixTransform):
    """FourierCoefficients generated from WFS slopes."""
    
    __mapper_args__ = {
            'polymorphic_identity':'fouriercoeffs',
        }
        
    MATRIX = "N"

class HEigenvalues(TelemetryGenerator):
    """The eiginvalues of the H matrix."""
    
    __mapper_args__ = {
            'polymorphic_identity':'heigenvalues',
        }
    
    def generate(self, dataset):
        """Generate an SVD dataset."""
        s = dataset.telemetry['slopes'].read()
        s = np.matrix(s)
        s.shape = (s.shape[0], s.shape[1], 1)
        
        vm = get_cm_projector(dataset.control_matrix)
        coeffs = vm * s
        hsvd = coeffs.view(np.ndarray).T
        
        with dataset.open() as g:
            g.create_dataset(self.h5path, data=hsvd)
        
    

