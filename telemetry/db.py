# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os, glob
import itertools
import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

import click

from celery import group

from .cli import cli, CeleryProgressGroup, ClickError, ClickGroup
from .tasks import read as read_task, refresh as refresh_task, rgenerate, generate
from .application import app
from .models import Base, Dataset, TelemetryKind, TelemetryPrerequisite, Instrument
from .models import (SlopeVectorX, SlopeVectorY, HCoefficients, 
    PseudoPhase, FourierCoefficients, HEigenvalues, PhaseToH, HwCoefficients)

class DatasetQuery(ClickGroup):
    """A query of datasets, filtered by command line arguments."""
    
    argument = "datasetquery"
    
    def __init__(self, date=None, dataset_id=None):
        super(DatasetQuery, self).__init__(date=date, dataset_id=dataset_id)
        
    def __call__(self, session, order=True, valid=True):
        """Produce a query from the session."""
        q = session.query(Dataset)
        if self.dataset_id is not None:
            click.echo("Sticking to dataset id={:d}".format(self.dataset_id))
            q = q.filter(Dataset.id==self.dataset_id)
        if valid is not None:
            q = q.filter(Dataset.valid==valid)
        if self.date is not None:
            click.echo("Limiting to datasets created around {0!s}".format(self.date))
            start = (self.date - datetime.timedelta(days=1))
            end = (self.date + datetime.timedelta(days=1))
            q = q.filter(Dataset.date.between(start, end))
        if self.instrument is not None:
            click.echo("Selecting only datasets from '{0:s}'".format(self.instrument))
            q = q.join(Dataset.instrument).filter(Instrument.name == self.instrument)
        if order:
            q = q.order_by(Dataset.created)
        return q
        
    @staticmethod
    def date(value):
        """Validate a date."""
        if value == "today":
            return datetime.datetime.now().date()
        return datetime.datetime.strptime(value, "%Y-%m-%d").date()
    
    @classmethod
    def decorate(cls, func):
        """docstring for decorate"""
        func = cls.option("--date", default=None, type=cls.date,
            name="date", help="Limit the query to a specific date.", envvar='TELEM_DATE')(func)
        func = cls.option("--instrument", default=None, type=str, help="Instrument Name", name='instrument')(func)
        func = cls.option("--id", default=None, type=int, help="Dataset ID", name='dataset_id')(func)
        func = super(DatasetQuery, cls).decorate(func)
        return func

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
    (PhaseToH, "H from Phase", "hphase"),
    (HwCoefficients, "Woofer Modal Coefficients", "hwcoefficients"),
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
    "hwcoefficients":["slopes"],
    "fouriercoeffs":["slopes"],
    "pseudophase":["slopes"],
    "sx":["slopes"],
    "sy":["slopes"],
    "hphase":["phase"]
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
@DatasetQuery.decorate
def show(datasetquery):
    """show datasets"""
    from astropy.table import Table
    with app.app_context():
        query = datasetquery(app.session).order_by(Dataset.created)
        if query.count() == 0:
            raise ClickError("No records found.")
        keys = ["created", "sequence", "rate", "closed", "gain", "bleed", "id"]
        t = Table([d.attributes() for d in query.all()])
        t[keys].more()

@cli.command()
@CeleryProgressGroup.decorate
@click.option("--instrument", type=str, help="Instrument Name", default=None)
@click.option("--force/--no-force", help="Force the read.", default=False)
@click.argument("paths", nargs=-1, type=click.Path(exists=False))
def read(progress, paths, instrument, force):
    """read data into the database."""
    with app.app_context():
        if not paths:
            paths = [os.path.join(app.config['TELEMETRY_ROOTDIRECTORY'], "*", "*", "data")]
        print(",".join("{0}".format(path) for path in paths))
        paths = (os.path.expanduser(os.path.join(os.path.splitext(path)[0], '*.hdf5')) for path in paths)
        paths = itertools.chain.from_iterable(glob.iglob(path) for path in paths)
        progress(read_task.si(filename, instrument_name=instrument, force=force) for filename in paths)
        
    

@cli.command()
@DatasetQuery.decorate
@CeleryProgressGroup.decorate
@click.option("--validate/--no-validate", default=False, help="Validate datasets.")
def refresh(datasetquery, progress, validate):
    """Refresh datasets."""
    with app.app_context():
        query = datasetquery(app.session, valid=None).order_by(Dataset.created)
        click.echo("Refreshing {:d} datasets. validate={!r}".format(query.count(), validate))
        progress(refresh_task.si(dataset.id, validate=validate) for dataset in query.all())
        
@cli.command()
@DatasetQuery.decorate
def delete(datasetquery):
    """Delete all the datasets"""
    with app.app_context():
        if click.confirm('Delete all the datasets?'):
            query = datasetquery(app.session, order=False)
            query.delete(synchronize_session='fetch')
            app.session.commit()
        
    

@cli.command()
@DatasetQuery.decorate
@CeleryProgressGroup.decorate
@click.argument("component", type=str)
@click.option("--recursive/--no-recursive", help="Recursively generate data.", default=False)
@click.option("--force/--no-force", help="Force regenerate.", default=False)
def make(datasetquery, progress, component, recursive, force):
    """Make a given component."""
    with app.app_context():
        kind = TelemetryKind.require(app.session, component)
        if not hasattr(kind, 'generate'):
            raise click.BadParameter("{0} does not appear to have a .generate() method.".format(kind))
        prerequisties = kind.rprerequisites
        
        done = app.session.query(Dataset.id).join(Dataset.kinds).filter(TelemetryKind.h5path == prerequisties[-1].h5path)
        if recursive:
            query = datasetquery(app.session).join(Dataset.kinds).filter(TelemetryKind.h5path == prerequisties[0].h5path)
            for p in prerequisties:
                query = p.filter(query)
        else:
            query = datasetquery(app.session).join(Dataset.kinds).filter(TelemetryKind.h5path == prerequisties[-2].h5path)
            query = kind.filter(query)
        
        if not force:
            query = query.filter(Dataset.id.notin_(done))
        
        click.echo("Generating {0} for {1} datasets.".format(kind.name, query.count()))
        click.echo("{0:d} datasets already have {1}".format(done.count(), kind.name))
        click.echo("Prerequisites:")
        for i, prereq in enumerate(kind.rprerequisites):
            click.echo("{:d}) {:s}".format(i, prereq.h5path))
        if recursive:
            progress(rgenerate(dataset, kind, force=force) for dataset in query.all())
        else:
            progress(generate.si(dataset.id, kind.id, force=force) for dataset in query.all())
    

@cli.command()
@click.argument("component", type=str)
@click.option("--recursive/--no-recursive", help="Recursively show data")
def graph(component, recursive):
    """Show the dependency graph to make a particular compoennt."""
    with app.app_context():
        kind = TelemetryKind.require(app.session, component)
        if not hasattr(kind, 'generate'):
            raise click.BadParameter("{0} does not appear to have a .generate() method.".format(kind))
        print("\n".join((prereq.name for prereq in kind.rprerequisites)))