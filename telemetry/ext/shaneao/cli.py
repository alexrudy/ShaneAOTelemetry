# -*- coding: utf-8 -*-
from telemetry.cli import cli
from telemetry.application import app
import click
import os
import lumberjack
import logging
from . import sequencer

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
    