# -*- coding: utf-8 -*-

import click
from telemetry.cli import cli, celery_progress
from telemetry.application import app
from telemetry.models import Dataset
from .tasks import pair

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
        progress(pair.si(dataset.id) for dataset in query.all())