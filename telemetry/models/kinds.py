# -*- coding: utf-8 -*-
"""
Data generators.
"""
import abc
from .case import TelemetryKind, Telemetry
from sqlalchemy.orm import validates
from telemetry.algorithms.coefficients import get_cm_projector, get_matrix
import numpy as np
import resource
from celery.utils.log import get_task_logger

__all__ = ['TelemetryGenerator', 'SlopeVectorX', 'SlopeVectorY', 
    'HCoefficients', 'HEigenvalues', 'PseudoPhase', 'FourierCoefficients']

def memory():
    """Get memory usage as a string."""
    from astropy.utils.console import human_file_size
    return human_file_size(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)

class TelemetryGenerator(TelemetryKind):
    
    __tablename__ = 'telemetrykind'
    
    @abc.abstractmethod
    def generate(self, dataset):
        """Generate data for a dataset."""
        return Telemetry(kind=self, dataset=dataset)
        
    def rgenerate(self, session, dataset, force=False):
        """Recursively generate data as required."""
        dataset.update(session)
        for prereq in self.rprerequisites[1:-1]:
            if prereq.h5path in dataset.telemetry and force:
                dataset.telemetry[prereq.h5path].remove()
            prereq.generate(dataset)
            dataset.telemetry[prereq.h5path] = Telemetry(kind=prereq, dataset=dataset)
        session.add(dataset)
        if self.h5path in dataset.telemetry and force:
            dataset.telemetry[self.h5path].remove()
        dataset.update(session)
        return self.generate(dataset)
    

class DerivedTelemetry(TelemetryGenerator):
    """Telemetry from derived telemetry."""
    
    H5PATH_ROOT = None
    POLYMORPHIC_KIND = None
    
    @validates('_kind')
    def validate_kind(self, key, value):
        """Force the telemetry kind of these objects to be 'periodogram'."""
        return self.POLYMORPHIC_KIND
    
    @validates('h5path')
    def validate_h5path(self, key, value):
        """Ensure that HDF5 paths contain periodogram."""
        if not value.startswith("{}/".format(self.H5PATH_ROOT)):
            value = "{}/".format(self.H5PATH_ROOT) + value
        return value
        
    @property
    def kind(self):
        """Base Kind."""
        return "/".join(self.h5path.split("/")[1:])
        


class SlopeVector(TelemetryGenerator):
    """Slope vector telemetry, splits slopes if necessary."""
    
    _NSLOPES = {
        16 : 144
    }
    
    def generate(self, dataset):
        """Generate data for a dataset."""
        s = dataset.telemetry['slopes'].read()
        n_across = int(dataset.instrument_data.mode.split('x',1)[0])
        ns = self._NSLOPES[n_across]
        idx = {'sx':0,'sy':1}[self.name]
        with dataset.open() as g:
            g.create_dataset(self.h5path, data=s[idx*ns:(idx+1)*ns,:])
        return super(SlopeVector, self).generate(dataset)
    
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
    OUTPUT_SHAPE = None
    
    def _get_source(self, dataset):
        """Get the source from a dataset."""
        return dataset.telemetry[self.SOURCE].read()
    
    def _postprocess(self, dataset, coeffs):
        """Postprocess the matrix multiply"""
        if self.OUTPUT_SHAPE is not None:
            coeffs.shape = self.OUTPUT_SHAPE
        return coeffs
    
    def _get_matrix(self, dataset):
        """Retrieve the appropriate matrix."""
        return get_matrix(self.MATRIX)
    
    def _apply_matrix(self, s, m):
        """Apply the matrix."""
        log = get_task_logger(__name__)
        coeffs = m.dot(s)
        coeffs = coeffs.view(np.ndarray)
        return coeffs
    
    def generate(self, dataset):
        """Generate data for a dataset."""
        m = self._get_matrix(dataset)
        s = self._get_source(dataset)
        coeffs = self._apply_matrix(s, m)
        del s
        coeffs = self._postprocess(dataset, coeffs)
        with dataset.open() as g:
            if self.h5path in g:
                del g[self.h5path]
            g.create_dataset(self.h5path, data=coeffs)
        del coeffs
        return super(MatrixTransform, self).generate(dataset)

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
    OUTPUT_SHAPE = (32, 32, -1)


class FourierCoefficients(MatrixTransform):
    """FourierCoefficients generated from WFS slopes."""
    
    __mapper_args__ = {
            'polymorphic_identity':'fouriercoeffs',
        }
        
    MATRIX = "N"
    OUTPUT_SHAPE = (32, 32, -1)
    
    def _postprocess(self, dataset, coeffs):
        """Postprocess the data."""
        coeffs = super(FourierCoefficients, self)._postprocess(dataset, coeffs)
        nc = int(dataset.instrument_data.mode.split('x',1)[0]) // 2
        
        s = np.fft.fftshift(coeffs, axes=(0,1))
        coeffs[...] = s
        del s
        
        if nc < (coeffs.shape[0] // 2):
            coeffs = coeffs[nc+1:-nc,nc+1:-nc].copy()
        return coeffs

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
        
        vm = get_cm_projector(dataset.instrument_data.control_matrix)
        coeffs = vm * s
        hsvd = coeffs.view(np.ndarray).T
        
        with dataset.open() as g:
            g.create_dataset(self.h5path, data=hsvd)
        return super(HEigenvalues, self).generate(dataset)
    

