# -*- coding: utf-8 -*-
"""
Helpers for views of ShadyAO
"""
from matplotlib.patches import Circle
def pupil_on_tweeter(ax, center=(15.5, 15.5), **kwargs):
    """Add the pupil"""
    
    kwargs.setdefault("fill", False)
    kwargs.setdefault("color", "k")
    kwargs.setdefault("lw", 2)
    ax.add_artist(Circle(center, 15.5, **kwargs))
    ax.add_artist(Circle(center, 3, **kwargs))
    
def hide_ticks(ax):
    """Hide all ticks on an axis."""
    ax.tick_params('both', bottom=False, left=False, labelbottom=False, labelleft=False)

    