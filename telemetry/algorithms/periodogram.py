# -*- coding: utf-8 -*-
import numpy as np
import astropy.units as u
from logging import getLogger

def periodogram(data, length=None, window=None, half_overlap=True, suppress_static=False, mean_remove=True, skip_length=0, start_length=0, clip_length=0, axis=0):
    """Make a periodogram from N-dimensional data. The periodogram is windowed by default. A custom window (which should be the same size as the expected output data) can be passed in at the window parameter.
    
    The default window is provided by :func:`cosine_window`
    
    :param ndarray data: The data to be made into a periodogram.
    :param int length: The length of the desired periodogram.
    :param ndarray window: The windowing function for the periodogram. If it is `None`, a standard windowing function will be used.
    :param bool half_overlap: Whether to half-overlap the segments of the periodogram.
    :param bool suppress_static: Whether to remove the static term from each individual segment. This won't remove static bleed.
    :param bool mean_remove: Whether to remove the overal static term, aligning the magnitude of all PSDs.
    :param int skip_length: A length over which to skip data at the end of each periodogram. Useful for clipping poorly behaved sections.
    :param int clip_length: A length over which to skip data at the end of the timeseries. Useful for clipping poorly behaved sections.
    :param int start_length: A length over which to skip data at the start of the timeseries. Useful for clipping poorly behaved sections.
    :param int axis: The axis along which to make the periodogram. This is normally the time-varying axis, and defaults to 0.
    
    """
    import scipy.fftpack
    
    log = getLogger(__name__ + ".periodogram")
    
    
    
    if (not isinstance(skip_length, int)) or skip_length < 0:
        raise ValueError("Parameter skip_length must be a non-negative integer. Got {!r}".format(skip_length))
    if skip_length > 0 and length is None:
        raise ValueError("Cannot use skip_length and not specify a full periodogram length.")
    
    total_length = data.shape[axis]
    if length is None:
        length = total_length
    
    if length > total_length:
        raise ValueError("Periodogram cannot be longer than data: data={}, periodogram={}".format(total_length, length))
    
    periodogram_length = length - 2*skip_length
    
    # Make the PSD Shape
    psd_shape = list(data.shape)
    psd_shape[axis] = periodogram_length
    psd_shape = tuple(psd_shape)
    
    log.debug("Building a ({}) -> ({}) periodogram".format("x".join(map("{:d}".format,data.shape)),"x".join(map("{:d}".format,psd_shape))))
    log.debug("Parameters: mean_remove={!r}, suppress_static={!r}, half_overlap={!r}, skip_length={!r}".format(mean_remove,suppress_static,half_overlap, skip_length))
    
    if window is None:
        window = extend_axes(cosine_window(periodogram_length), len(psd_shape), fixed_axis=axis)
    
    data = u.Quantity(data)
    if mean_remove:
        data = data - u.Quantity(np.expand_dims(data.mean(axis=axis),axis=axis), unit=data.unit)
    
    psd = np.zeros(psd_shape,dtype=np.complex)
    interval_iterator = periodogram_slices(length, total_length, len(psd_shape), half_overlap=half_overlap, skip_length=skip_length, axis=axis, start_length=start_length, clip_length=clip_length)
    
    num_intervals = 0
    for select in interval_iterator:
        segment = data[select]
        if suppress_static:
            segment -= segment.mean()
        psd += np.power(np.abs(scipy.fftpack.fft(segment * window, axis=axis)), 2.0)
        num_intervals += 1
    psd = np.real(psd)
    psd = psd / (num_intervals)
    psd = psd / np.sum(window**2.0, axis=axis)
    psd = psd / periodogram_length
    return scipy.fftpack.fftshift(psd, axes=axis)
    
def periodogram_slices(length, total_length, ndim, half_overlap=True, skip_length=0, start_length=0, clip_length=0, axis=0):
    """Compute and generate the slices for a periodogram with given overlap settings, etc."""
    if skip_length != 0 and half_overlap:
        log.warning("Ignoring half_overlap=True when skip_length={:d} is nonzero.".format(skip_length))
        half_overlap = False
    
    periodogram_length = length - 2*skip_length
    data_length = total_length - start_length - clip_length
    
    if half_overlap:
       num_intervals = np.floor(data_length/(length/2)) - 1
       start_indices = np.arange(num_intervals)*length/2
    else:
       num_intervals = np.floor(data_length/(length))
       start_indices = np.arange(num_intervals)*length
       
    start_indices += start_length
    select = [ slice(None) for i in range(ndim) ]
    for a in start_indices:
        select[axis] = slice(a+skip_length,a+periodogram_length+skip_length)
        assert select[axis].stop - select[axis].start == periodogram_length
        yield tuple(select)
    
def periodogram_mask(length, total_length, half_overlap=True, skip_length=0, start_length=0, clip_length=0):
    """Produce a mask of a periodogram showing what regions are accessible, and which arent."""
    mask = np.zeros((total_length,), dtype=bool)
    for select in periodogram_slices(length, total_length, 1, half_overlap=half_overlap, skip_length=skip_length, start_length=start_length, clip_length=clip_length):
        mask[select] = True
    return mask
    
def periodogram_excludes(length, total_length, half_overlap=True, skip_length=0, start_length=0, clip_length=0):
    """Return the excluded regions."""
    start = 0.0
    for select, in periodogram_slices(length, total_length, 1, half_overlap=half_overlap, skip_length=skip_length, start_length=start_length, clip_length=clip_length):
        stop = select.start
        if (start < stop) and (stop > 0.0):
            yield (start, stop)
        start = select.stop
    if start < total_length - 1:
        stop = total_length - 1
        yield (start, stop)
    
def extend_axes(array, ndim, fixed_axis=0):
    """Expand the dimensions of a numpy array."""
    if isinstance(fixed_axis, int):
        fixed_axis = (fixed_axis,)
    for dim in range(ndim):
        if dim not in fixed_axis:
            array = np.expand_dims(array, axis=dim)
    return array
    
def cosine_window(periodogram_length):
    """A cosine-based periodogram window.
    
    The window is
    
    .. math::
        w(x) = 0.42 - 0.5 \cos(2 \pi x / l) + 0.08 \cos(4 \pi x / l)
        
    where :math:`l` is the length of the periodogram, and :math:`x` is the position along that periodogram.
    
    """
    ind = np.arange(periodogram_length,dtype=np.float)
    window = 0.42 - 0.5*np.cos(2.0*np.pi*ind/(periodogram_length-1)) + 0.08*np.cos(4.0*np.pi*ind/(periodogram_length-1))
    return window