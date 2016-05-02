# -*- coding: utf-8 -*-

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

import click
from .cli import cli
from .application import app
from .models import Dataset, TelemetryKind, TelemetryPrerequisite
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
def initdb():
    """initialize the database"""
    click.echo("Initializing the database at '{0}'.".format(app.config['SQLALCHEMY_DATABASE_URI']))
    with app.app_context():
        click.echo("Creating all tables.")
        app.create_all()
        
        click.echo("Setting up database constants.")
        for _type, name, h5path in KINDS:
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
        