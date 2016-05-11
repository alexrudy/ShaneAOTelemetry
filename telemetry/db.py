# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os, glob
import itertools
import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

import click

from celery import group

from .cli import cli, celery_progress, ClickError
from .tasks import read as read_task, refresh as refresh_task, rgenerate
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
@click.option("--date", help="Limit the table to a single date.", default=None)
def show(date):
    """show datasets"""
    from astropy.table import Table
    with app.app_context():
        query = app.session.query(Dataset).order_by(Dataset.created)
        if date is not None:
            s_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            e_date = s_date + datetime.timedelta(days=1)
            click.echo("Showing data created on {0}".format(s_date))
            query = query.filter(Dataset.date.between(s_date,e_date))
        if query.count() == 0:
            raise ClickError("No records found.")
        keys = ["created", "sequence", "rate", "closed", "gain", "bleed"]
        t = Table([d.attributes() for d in query.all()])
        t[keys].more()

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
def refresh(progress):
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
        
    

@cli.command()
@celery_progress
@click.argument("component", type=str)
@click.option("--recursive/--no-recursive", help="Recursively generate data.", default=False)
@click.option("--force/--no-force", help="Force regenerate.", default=False)
def make(progress, component, recursive, force):
    """Make a given component."""
    with app.app_context():
        kind = TelemetryKind.require(app.session, component)
        if not hasattr(kind, 'generate'):
            raise click.BadParameter("{0} does not appear to have a .generate() method.".format(kind))
        prerequisties = kind.rprerequisites
        
        done = app.session.query(Dataset.id).join(Dataset.kinds).filter(TelemetryKind.h5path == prerequisties[-1].h5path)
        if recursive:
            query = app.session.query(Dataset).join(Dataset.kinds).filter(TelemetryKind.h5path == prerequisties[0].h5path)
            for p in prerequisties:
                query = p.filter(query)
        else:
            query = app.session.query(Dataset).join(Dataset.kinds).filter(TelemetryKind.h5path == prerequisties[-2].h5path)
            query = kind.filter(query)
        
        if not force:
            query = query.filter(Dataset.id.notin_(done))
        
        click.echo("Generating {0} for {1} datasets.".format(kind.name, query.count()))
        click.echo("{0:d} datasets already have {1}".format(done.count(), kind.name))
        click.echo("Prerequisites:")
        for i, prereq in enumerate(kind.rprerequisites):
            click.echo("{:d}) {:s}".format(i, prereq.h5path))
        progress(group(rgenerate(dataset, kind) for dataset in query.all()))