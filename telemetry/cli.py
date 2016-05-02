# -*- coding: utf-8 -*-
"""
Basic command line tools.
"""
import click
import argparse
import datetime
import time
from telemetry.models import Dataset, TelemetryKind
from sqlalchemy.sql import between
from astropy.utils.console import ProgressBar

__all__ = ['progress', 'cli']

def progress(resultset):
    """A group result progressbar."""
    with ProgressBar(len(resultset)) as pbar:
        pbar.update(0)
        while not resultset.ready():
            pbar.update(resultset.completed_count())
            time.sleep(0.1)
        pbar.update(resultset.completed_count())
    return
    
@click.group()
def cli():
    pass

def add_date_filter(date, days, query):
    """Add the date fileter."""

    start_date = date
    end_date = (date + datetime.timedelta(days=days))
    return query.filter(between(Dataset.created,start_date,end_date))

def parser(setup, **kwargs):
    """Make an argument parser"""
    parser = argparse.ArgumentParser(**kwargs)
    parser.add_argument("-f", "--force", help="Force this operation to complete.", action='store_true')
    if setup is not None:
        setup(parser)
    
    group = parser.add_argument_group("query filtering")
    group.add_argument("-d", "--date", type=lambda s : datetime.datetime.strptime(s, "%Y-%m-%d"), help="Limit query to a single date.")
    group.add_argument("--days", type=int, help="Number of days to query", default=1)
    
    opt = parser.parse_args()
    opt.error = parser.error
    
    if opt.date:
        def filter_date(query):
            """Filter a query."""
            return add_date_filter(opt.date, opt.days, query)
        opt.filter = filter_date
    else:
        opt.filter = lambda q : q
    return opt