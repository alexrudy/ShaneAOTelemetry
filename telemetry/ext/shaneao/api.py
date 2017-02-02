# -*- coding: utf-8 -*-
"""
API tools for querying against ShaneAO telemetry.
"""
import numpy as np
from controltheory.periodogram import periodogram

from .models import ShaneAOInfo
from ...models import TelemetryKind, Dataset, Instrument, Telemetry

__all__ = ['query_by_telemetry_kind', 'ShaneAOInfo', 'Dataset', 'periodogram_chunked']

def query_by_telemetry_kind(kind, session):
    """Query by telemetry kind"""
    kind = TelemetryKind.require(session, kind)
    query = session.query(Telemetry).join(Dataset).join(Instrument).filter(Instrument.name == u'ShaneAO')
    query = query.join(Telemetry.kind).filter(TelemetryKind.id == kind.id)
    query = query.join(Dataset.instrument_data).join(ShaneAOInfo)
    return query
    
def periodogram_chunked(data, **kwargs):
    """Periodogram a chunked dataset."""
    chunk = int(kwargs.pop('chunk', 4096))
    axis = range(data.ndim)[int(kwargs.get('axis', 0))]
    
    shape = list(data.shape)
    shape[axis] = int(kwargs.get('length'))
    chunks = data.shape[axis] // chunk
    
    psds = data.__array_wrap__(np.empty(tuple(shape) + (chunks,)))
    cshape = list(data.shape)
    cshape[axis] = chunk
    cshape.insert(axis, -1)
    cdata = data.reshape(tuple(cshape))
    
    for i, chunk in enumerate(iter(np.rollaxis(cdata, axis))):
        psds[..., i] = periodogram(chunk, **kwargs)
    return psds.mean(axis=-1)