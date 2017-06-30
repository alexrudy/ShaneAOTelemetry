# -*- coding: utf-8 -*-
"""
Helpers for views of ShadyAO
"""
import astropy.units as u
from matplotlib.patches import Circle

def pupil_on_tweeter(ax, center=(15.5, 15.5), **kwargs):
    """Add the pupil to axes which are on tweeter gridpoints."""
    
    kwargs.setdefault("fill", False)
    kwargs.setdefault("color", "k")
    kwargs.setdefault("lw", 1)
    r_primary = kwargs.pop('primary_radius', 15.5)
    r_secondary = kwargs.pop('secondary_radius', 3.0)
    fill_secondary = kwargs.pop('fill_secondary', True)
    ax.add_artist(Circle(center, r_primary, **kwargs))
    kwargs['fill'] = fill_secondary
    ax.add_artist(Circle(center, r_secondary, **kwargs))
    
def hide_ticks(ax):
    """Hide all ticks on an axis."""
    ax.tick_params('both', bottom=False, left=False, labelbottom=False, labelleft=False)

positions = {
    'UL': ((0.05, 0.95), dict(va='top', ha='left')),
    'UR': ((0.95, 0.95), dict(va='top', ha='right')),
    'LR': ((0.95, 0.05), dict(va='bottom', ha='right')),
}

def ax_label(axes, cln, oln, date, rate, *extra, **kwargs):
    """Label axes for telemetry plots."""
    rate = u.Quantity(rate, u.Hz)
    parts = ["Closed #{cln:04d} / Open #{oln:04d}".format(cln=cln, oln=oln), "from {date:%Y/%m/%d} at {rate.value:.0f}Hz".format(date=date, rate=rate)]
    container = axes.bbox.padded(-10)
    parts.extend(extra)
    pos, pkwargs = positions[kwargs.pop('position', 'UR')]
    kwargs.update(pkwargs)
    px, py = pos
    text = axes.text(px, py, "\n".join(parts), transform=axes.transAxes, multialignment='left',
                     fontsize='x-small', bbox=dict(fc='white', alpha=0.8, boxstyle='round'), **kwargs)
    return text    