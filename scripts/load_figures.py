#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A script to load figures into the database.
"""

from __future__ import unicode_literals

import os
import glob
import datetime
import click
from telemetry.application import app
from telemetry.models import Figure, Dataset
from sqlalchemy import func

@click.command()
def main():
    """Load figure objects into database."""
    with app.app_context():
        root = os.path.join(app.config['TELEMETRY_ROOTDIRECTORY'], "ShaneAO")
        for filepath in glob.iglob(os.path.join(root, "*", "figures", "*", "*", "*.png")):
            # First, is this already in the database?
            c = app.session.query(Figure).filter(Figure.filepath==filepath).count()
            if c == 1:
                continue
            elif c > 1:
                # Purge them all, if we find more than one.
                app.session.query(Figure).filter(Figure.filepath==filepath).delete()
            
            # Set the dataset parts
            parts = filepath.split(os.path.sep)
            created = datetime.datetime.strptime(parts[-5], "%Y-%m-%d").date()
            sequence = int(parts[-3][1:])
            telpath = parts[-2].replace(".","/")
            query = app.session.query(Dataset).filter(func.date_trunc("day",Dataset.created) == created)
            query = query.filter(Dataset.sequence == sequence)
            dataset = query.one_or_none()
            if dataset is None:
                click.echo("Dataset missing for '{0}'".format(filepath))
                continue
            telemetry = dataset.telemetry[telpath]
            fig = Figure(filepath=filepath, telemetry=telemetry, figure_type=parts[-1].split(".")[0])
            app.session.add(fig)
            click.echo("Added '{0}'".format(filepath))
        app.session.commit()
        
    
if __name__ == '__main__':
    main()