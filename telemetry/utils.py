# -*- coding: utf-8 -*-
import os
import datetime as dt
__all__ = ['makedirs', 'previous_noon', 'parse_dt']

def makedirs(dirname):
    """Make directories."""
    if os.path.exists(dirname):
        return
    try:
        os.makedirs(dirname)
    except OSError as e:
        if not os.path.exists(dirname):
            raise
        

def previous_noon(now=None):
    """Compute the previous noon for telemetry folders."""
    noon = dt.time(12, 0, 0)
    if now is None:
        now = dt.datetime.now()
    if now.hour >= 12:
        return dt.datetime.combine(now.date(), noon)
    else:
        yesterday = (now - dt.timedelta(days=1))
        return dt.datetime.combine(yesterday.date(), noon)
    
def parse_dt(value):
    """Return date"""
    if not value or isinstance(value, dt.datetime):
        return previous_noon(value)
    return dt.datetime.strptime(value, "%Y-%m-%d").date()
    