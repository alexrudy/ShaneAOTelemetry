# -*- coding: utf-8 -*-
from __future__ import absolute_import

"""
Basic command line tools.
"""

import click
import argparse
import datetime
import time
import itertools
from celery import group
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
    
class CeleryProgressGroup(object):
    """A state management for celery progress."""
    def __init__(self, try_one=False, wait=True, limit=None):
        super(CeleryProgressGroup, self).__init__()
        self.try_one = try_one
        self.wait = wait
        self.limit = limit
        
    @classmethod
    def callback(cls, name):
        """Get an option callback."""
        def callback(ctx, param, value):
            state = ctx.ensure_object(cls)
            setattr(state, name, value)
            return value
        return callback
        
    def __call__(self, iterator):
        """Call the progress."""
        if self.limit is not None:
            iterator = itertools.slice(iterator, 0, self.limit)
        g = group(iterator)
        if self.try_one:
            click.echo("Trying a single task:")
            r = next(iter(g)).delay().get()
            click.echo("Success! {0}".format(r))
        r = g.delay()
        if self.wait:
            progress(r)
        else:
            click.echo("Tasks started for group {0}".format(r.id))
        return r

pass_progress_group = click.make_pass_decorator(CeleryProgressGroup, ensure=True)

def celery_progress(func):
    """A decorator to add celery progress options to a function."""
    func = click.option("--try-one/--no-try", default=False,
        callback=CeleryProgressGroup.callback("try_one"), 
        expose_value=False, help="Try a single value")(func)
    func = click.option("--limit", type=int, default=None,
        callback=CeleryProgressGroup.callback("limit"),
        expose_value=False, help="Limit the number of tasks to process.")(func)
    func = click.option("--wait/--no-wait", default=True,
        callback=CeleryProgressGroup.callback("wait"),
        expose_value=False, help="Wait for tasks to finish.")(func)
    func = pass_progress_group(func)
    return func


