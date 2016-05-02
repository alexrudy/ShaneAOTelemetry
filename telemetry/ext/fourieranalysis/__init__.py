# -*- coding: utf-8 -*-
from __future__ import absolute_import

def setup(app):
    """The setup entry point for this extension."""
    from telemetry import db
    
    # Connect the models.
    from . import models
    
    # Connect the DB initializer.
    db.INITIALIZERS.add(models.initdb)