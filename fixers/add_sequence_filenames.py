#!/usr/bin/env python
# -*- coding: utf-8 -*-

from telemetry.application import app
from telemetry.ext.shaneao.models import ShaneAODataSequence
from telemetry.models import Dataset

import os
import click

@click.command()
def main():
    """Main actions."""
    with app.app_context():
        root = os.path.join(app.config['TELEMETRY_ROOTDIRECTORY'], "ShaneAO")
        click.echo("Setting sequence filenames.")
        click.echo("  Data root: {0}".format(root))
        for sequence in app.session.query(ShaneAODataSequence).join(ShaneAODataSequence.frames).all():
            base = os.path.join(root, sequence.frames[0].created.date().strftime("%Y-%m-%d"), "data")
            sequence.filename = os.path.join(base,"telemetry_{0:04d}.hdf5".format(sequence.id))
            app.session.add(sequence)
        app.session.commit()
        
        click.echo("Mapping sequences to datasets.")
        query = app.session.query(ShaneAODataSequence, Dataset)
        query = query.join(Dataset, ShaneAODataSequence.filename == Dataset.filename)
        for sequence, dataset in query.all():
            sequence.dataset = dataset
            dataset.created = sequence.starttime
            dataset.date = None
            app.session.add(sequence)
            app.session.add(dataset)
        app.session.commit()

if __name__ == '__main__':
    main()