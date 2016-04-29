# -*- coding: utf-8 -*-
"""
Basic command line tools.
"""
import argparse
import datetime
from telemetry.models import Dataset, TelemetryKind
from sqlalchemy.sql import between

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
    
    from telemetry import connect
    
    Session = connect()
    opt.session = Session()
    
    query = opt.session.query(Dataset.id)
    if opt.date:
        query = add_date_filter(opt.date, opt.days, query)
        def filter_date(query):
            """Filter a query."""
            return add_date_filter(opt.date, opt.days, query)
        opt.filter = filter_date
    else:
        opt.filter = lambda q : q
    opt.query = query
    return opt