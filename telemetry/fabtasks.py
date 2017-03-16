from fabric.api import *
import os.path
from os.path import join as pjoin, sep
import contextlib
import datetime as dt

BASE = os.path.dirname(__file__)

env.use_ssh_config = True

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
    if value is None or isinstance(value, dt.datetime):
        return previous_noon(value)
    return dt.datetime.strptime(value, "%Y-%m-%d").date()
    

@task
@hosts("real")
def pull(date=None):
    """rsync telemetry data from real to r2d2"""
    # rsync -avP user@real:telemetry/2017-03-15/*.hdf5 /Volumes/LaCie/Telemetry2/ShaneAO/2017-03-15/
    date = parse_dt(date)
    telroot = pjoin(sep + 'Volumes','LaCie','Telemetry2','ShaneAO', "{0:%Y-%m-%d}".format(date)) + sep
    remroot = pjoin(sep + 'local', 'data', 'telemetry', "{0:%Y-%m-%d}".format(date)) + sep

    local("mkdir -p {0}".format(telroot))
    cmd = ['rsync', '-avP', '{0:s}:{1}'.format(env.host_string, remroot), telroot]
    local(" ".join(cmd))
