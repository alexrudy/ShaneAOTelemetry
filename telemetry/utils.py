# -*- coding: utf-8 -*-
import os

__all__ = ['makedirs']

def makedirs(dirname):
    """Make directories."""
    if os.path.exists(dirname):
        return
    try:
        os.makedirs(dirname)
    except OSError as e:
        if not os.path.exists(dirname):
            raise
        