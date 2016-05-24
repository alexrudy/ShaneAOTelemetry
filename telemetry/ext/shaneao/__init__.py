# -*- coding: utf-8 -*-

from __future__ import absolute_import

from telemetry import db

def setup(app):
    """The setup entry point for this extension."""
    
    # Connect the models.
    from . import models
    from . import cli
    
    # Connect the DB initializer.
    # db.INITIALIZERS.add(models.initdb)