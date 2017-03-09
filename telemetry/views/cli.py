# -*- coding: utf-8 -*-

from ..cli import cli, CeleryProgressGroup
from ..db import DatasetQuery
from ..application import app
from ..models import TelemetryKind, Dataset
from . import timeseries as ts
import click

@cli.group()
def plot():
    """The plotting group."""
    pass

def decorate_plotting_command(func):
    """A decorator to make a plotting command."""
    func = DatasetQuery.decorate(func)
    func = CeleryProgressGroup.decorate(func)
    func = click.argument("component", type=str)(func)
    func = click.option("--force/--no-force", default=False, help="Force update plots.")(func)
    return func

def plotting_command(name, task, **kwargs):
    """Make a plotting command from a task."""
    
    group = kwargs.pop('group', plot)
    component_name_transform = kwargs.pop('component_name_transform', lambda s : s)
    
    @group.command(name=name)
    @decorate_plotting_command
    def _command(datasetquery, progress, component, force):
        with app.app_context():
            kind = TelemetryKind.require(app.session, component_name_transform(component))
            datasets = datasetquery(app.session).join(Dataset.kinds).filter(TelemetryKind.id == kind.id)
            if not datasets.count():
                click.echo("No datasets to plot with {0}".format(kind))
            progress(task.si(dataset.id, kind.id, force=force, **kwargs) for dataset in datasets.all())
    _command.__doc__ = task.__doc__
    return _command
    

timeseries = plotting_command('timeseries', ts.timeseries, category='timeseries')
ltdtimeseries = plotting_command('ltdtimeseries', ts.timeseries, category="timeseries.ltd", select=[0,10,20,30,40,50], color=None, alpha=0.5)
histogram = plotting_command('histogram', ts.histogram)
mean = plotting_command('mean', ts.mean)


@plot.command()
@decorate_plotting_command
@click.option("--tlimit", type=int, help="Time limit.")
def movie(datasetquery, progress, component, force, tlimit):
    """A movie of a single component."""
    with app.app_context():
        kind = TelemetryKind.require(app.session, component)
        datasets = datasetquery(app.session).join(Dataset.kinds).filter(TelemetryKind.id == kind.id)
        progress(make_movie.si(dataset.id, component, force=force, limit=tlimit) for dataset in datasets.all())
    