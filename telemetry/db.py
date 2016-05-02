# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os, glob
import itertools

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

import click

from celery import group

from .cli import cli, celery_progress
from .tasks import read as read_task, refresh as refresh_task
from .application import app
from .models import Base, Dataset, TelemetryKind, TelemetryPrerequisite
from .models import (SlopeVectorX, SlopeVectorY, HCoefficients, 
    PseudoPhase, FourierCoefficients, HEigenvalues)

def add_prerequisite(session, source, prerequisite):
    """Add a prerequisite."""
    if prerequisite not in source.prerequisites:
        tp = TelemetryPrerequisite(source=source, prerequisite=prerequisite)
        session.add(tp)

INITIALIZERS = set()

KINDS = [
    (HEigenvalues, "H Eigenvalues", "heigenvalues"),
    (HCoefficients, "H Coefficients", "hcoefficients"),
    (FourierCoefficients, "FourierCoefficients", "fouriercoeffs"),
    (PseudoPhase, "Pseudo Phase", "pseudophase"),
    (SlopeVectorX, "X Slopes", "sx"),
    (SlopeVectorY, "Y Slopes", "sy"),
    (TelemetryKind, "Slopes", "slopes"),
    (TelemetryKind, "Tweeter Actuators", "tweeter"),
    (TelemetryKind, "Woofer Actuators", "woofer"),
    (TelemetryKind, "Filter Coefficients", "filter"),
    (TelemetryKind, "Tip/Tilt Values", "tiptilt"),
    (TelemetryKind, "Uplink Tip/Tilt Values", "uplink"),
    (TelemetryKind, "Intermediate Hybrid Matrix Values", "intermediate"),
]
PREREQS = {
    "heigenvalues":["slopes"],
    "hcoefficients":["slopes"],
    "fouriercoeffs":["slopes"],
    "pseudophase":["slopes"],
    "sx":["slopes"],
    "sy":["slopes"],
}

@cli.command()
@click.option("--echo/--no-echo", default=False)
def initdb(echo):
    """initialize the database"""
    click.echo("Initializing the database at '{0}'.".format(app.config['SQLALCHEMY_DATABASE_URI']))
    app.config['SQLALCHEMY_ECHO'] = echo
    with app.app_context():
        click.echo("Creating all tables.")
        app.create_all()
        
        click.echo("Setting up database constants.")
        for _type, name, h5path in KINDS:
            click.echo("{!r}".format(_type))
            _type.require(app.session, name, h5path)
        app.session.commit()
        
        for h5path, prerequisites in PREREQS.items():
            kind = app.session.query(TelemetryKind).filter(TelemetryKind.h5path==h5path).one()
            for prereq in prerequisites:
                prereq = app.session.query(TelemetryKind).filter(TelemetryKind.h5path==prereq).one()
                kind.add_prerequisite(app.session, prereq)
            
        for initializer in INITIALIZERS:
            initializer(app.session)
        
        app.session.commit()
        
    

@cli.command()
@celery_progress
@click.option("--force/--no-force", help="Force the read.", default=False)
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
def read(progress, paths, force):
    """read data into the database."""
    with app.app_context():
        if not paths:
            paths = [os.path.join(app.config['TELEMETRY_ROOTDIRECTORY'], "**", "**", "raw")]
        print(paths)
        paths = (os.path.expanduser(os.path.join(os.path.splitext(path)[0], '*.hdf5')) for path in paths)
        paths = itertools.chain.from_iterable(glob.iglob(path) for path in paths)
        progress(read_task.si(filename, force=force) for filename in paths)
        
    

@cli.command()
@celery_progress
def refresh():
    """Refresh datasets."""
    with app.app_context():
        query = app.session.query(Dataset).order_by(Dataset.created)
        click.echo("Refreshing {:d} datasets.".format(query.count()))
        progress(refresh_task.si(dataset.id) for dataset in query.all())
        
@cli.command()
def delete():
    """Delete all the datasets"""
    with app.app_context():
        if click.confirm('Delete all the datasets?'):
            query = app.session.query(Dataset)
            query.delete(synchronize_session='fetch')
            app.session.commit()
        