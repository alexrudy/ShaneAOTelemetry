# -*- coding: utf-8 -*-

import click
from telemetry.cli import cli, celery_progress
from telemetry.application import app
from telemetry.models import Dataset, TelemetryKind, Telemetry
from . import tasks

@cli.group()
def fa():
    """Fourier Analysis group."""
    pass


@fa.command()
@celery_progress
def sequence(progress):
    """Sequence datasets."""
    with app.app_context():
        query = app.session.query(Dataset).order_by(Dataset.created)
        click.echo("Sequencing {0:d} datasets.".format(query.count()))
        progress(tasks.pair.si(dataset.id) for dataset in query.all())
        

@fa.command()
@click.argument("component", type=str)
@click.option("--force/--no-force", help="Force regenerate.", default=False)
@celery_progress
def transferfunction(progress, component, force):
    """Make a transfer function"""
    with app.app_context():
        tf_path = "transferfunction/{0}".format(component)
        pg_path = "periodogram/{0}".format(component)
        kind = TelemetryKind.require(app.session, tf_path)
        if not hasattr(kind, 'generate'):
            raise click.BadParameter("{0} does not appear to have a .generate() method.".format(component))
            
        e_query = app.session.query(Dataset.id).join(Telemetry).join(TelemetryKind).filter(TelemetryKind.h5path == pg_path)
        t_query = app.session.query(Dataset.id).join(Telemetry).join(TelemetryKind).filter(TelemetryKind.h5path == tf_path)
        query = app.session.query(Dataset).filter(Dataset.id.in_(e_query)).join(Dataset.pairs)
        
        click.echo("{0:d} potential target datasets.".format(query.count()))
        
        if not force:
            query = query.filter(Dataset.id.notin_(t_query))
    
        click.echo("Generating {0} for {1} datasets.".format(kind.name, query.count()))
        click.echo("{0:d} datasets already have {1}".format(t_query.count(), kind.name))
        
        progress(tasks.transferfunction.si(dataset.id, opt.kind) for dataset in query.all())
    

@fa.command()
@click.argument("component", type=str)
@click.option("--force/--no-force", help="Force regenerate.", default=False)
@celery_progress
def tfplot(progress, component, force):
    """Plot transfer functions"""
    with app.app_context():
        tf_path = "transferfunction/{0}".format(component)
        query = app.session.query(Dataset).order_by(Dataset.created).join(Telemetry).join(TelemetryKind).filter(TelemetryKind.h5path == tf_path)
        click.echo("Plotting transfer functions for {0:d} datasets.".format(query.count()))
        progress(tasks.transferfunction_plot.si(dataset.id, component) for dataset in query.all())