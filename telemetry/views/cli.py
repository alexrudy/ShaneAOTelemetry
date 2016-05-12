# -*- coding: utf-8 -*-

from ..cli import cli, celery_progress
from ..application import app
from ..models import TelemetryKind, Dataset
from .timeseries import make_timeseries, make_histogram
import click

@cli.command()
@celery_progress
@click.argument("component", type=str)
def timeseries(progress, component):
    """Time series."""
    with app.app_context():
        kind = TelemetryKind.require(app.session, component)
        datasets = app.session.query(Dataset).join(Dataset.kinds).filter(TelemetryKind.id == kind.id)
        progress(make_timeseries.si(dataset.id, component) for dataset in datasets.all())
    
@cli.command()
@celery_progress
@click.argument("component", type=str)
def histogram(progress, component):
    """Time series."""
    with app.app_context():
        kind = TelemetryKind.require(app.session, component)
        datasets = app.session.query(Dataset).join(Dataset.kinds).filter(TelemetryKind.id == kind.id)
        progress(make_histogram.si(dataset.id, component) for dataset in datasets.all())