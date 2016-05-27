# -*- coding: utf-8 -*-
from telemetry.cli import cli, CeleryProgressGroup
from telemetry.db import DatasetQuery

from telemetry.application import app
from telemetry.models import Instrument, Dataset
import click
import celery
import os
import glob
import time
import lumberjack
import logging
from . import sequencer
from . import retrieve
from . import models

@cli.group()
def shaneao():
    """Controller group for ShaneAO telemetry."""
    pass
    
@shaneao.command()
@click.option('--quiet/--not-quiet', default=False, help="Make output quiet")
@click.option('--verbose/--not-verbose', default=False, help="Make output verbose")
@click.option("--force/--no-force", help="Force the upgrade.", default=False)
@click.option("--limit", type=int, default=None, help="Limit the number of tasks to process.")
@click.argument('paths', nargs=-1)
def upgrade(paths, quiet, verbose, force, limit):
    """Upgrade (sequence) files."""
    verbose = (verbose and not quiet)
    if verbose:
        lumberjack.setup_logging(mode='stream', level=1)
    elif quiet:
        lumberjack.setup_logging(mode='stream', level=logging.ERROR)
    else:
        lumberjack.setup_logging(mode='stream', level=logging.INFO)
    root = os.path.join(app.config['TELEMETRY_ROOTDIRECTORY'], "ShaneAO")
    click.echo("Outputting to {0}".format(root))
    sequencer.upgrade(paths, root, quiet=quiet, verbose=verbose, force=force, limit=limit)
    
@shaneao.command()
@click.option('--verbose/--not-verbose', default=False, help="Make output verbose")
@click.option('--continuous/--not-continuous', default=False, help="Continuous ")
def download(verbose=False, continuous=False):
    """Download data."""
    if verbose:
        lumberjack.setup_logging(mode='stream', level=1)
    else:
        lumberjack.setup_logging(mode='stream', level=logging.INFO)
    root = os.path.join(app.config['TELEMETRY_ROOTDIRECTORY'], "ShaneAO")
    proc = retrieve.rsync_telemetry(root)
    if continuous:
        try:
            click.echo("Press ^C to end downloading.")
            while not proc.returncode:
                proc.wait()
                time.sleep(1.0)
                proc = retrieve.rsync_telemetry(root)
        except KeyboardInterrupt:
            click.echo("")
    else:
        proc.wait()
    click.secho("Done.", fg='green')
    return proc.returncode
    
@shaneao.command()
@CeleryProgressGroup.decorate
@click.option("--force/--no-force", default=False, help="Force the update.")
@click.argument("path")
def new(progress, path, force=False):
    """Take the required actions for the new file."""
    root = os.path.join(app.config['TELEMETRY_ROOTDIRECTORY'], "ShaneAO")
    progress(retrieve.new_file_to_sequence(p, root, force=force) for p in glob.iglob(path))
    
@shaneao.command()
def purge_sequences():
    """Purge sequences"""
    with app.app_context():
        if click.confirm("Delete all the ShaneAO Sequences?"):
            app.session.query(models.ShaneAODataSequence).delete()
            app.session.commit()

@shaneao.command()
@CeleryProgressGroup.decorate
@click.option("--force/--no-force", default=False, help="Force the update.")
def concatenate(progress, force):
    """Concatenate sequences."""
    with app.app_context():
        root = os.path.join(app.config['TELEMETRY_ROOTDIRECTORY'], "ShaneAO")
        progress(retrieve.concatenate_all_sequences(app.session, root, force))
    
@shaneao.command()
@CeleryProgressGroup.decorate
@click.option("--force/--no-force", default=False, help="Force the update.")
def load(progress, force=False):
    """Load ShaneAO data."""
    root = os.path.join(app.config['TELEMETRY_ROOTDIRECTORY'], "ShaneAO")
    progress(retrieve.load.si(root=root, date=directory.split(os.path.sep)[-1], force=force) for directory in glob.iglob(os.path.join(root, "*")) if os.path.isdir(directory))
    
@shaneao.command()
@DatasetQuery.decorate
@CeleryProgressGroup.decorate
def map(datasetquery, progress):
    """Map sequences together"""
    with app.app_context():
        instrument = app.session.query(Instrument).filter(Instrument.name=='ShaneAO').one()
        query = datasetquery(app.session).filter(Dataset.instrument==instrument).order_by(Dataset.created)
        click.echo("ShaneAO Mapping {:d} datasets.".format(query.count()))
        progress(retrieve.map_sequence.si(dataset.id) for dataset in query.all())
    