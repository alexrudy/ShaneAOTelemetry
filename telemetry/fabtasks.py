from fabric.api import *
import os.path
from glob import iglob
import re
import h5py
from os.path import join as pjoin, sep
import contextlib
import datetime as dt
from .utils import previous_noon, parse_dt

env.use_ssh_config = True

__all__ = ['ql', 'pull']

def parse_bool(value):
    if isinstance(value, (str, bytes)):
        if value.lower() in ("yes", "y", "true", "t"):
            return True
        elif value.lower() in ("no", "n", "false", "f"):
            return False
        raise ValueError("Bool: {0!r}".format(value))
    return bool(value)

def is_closed_loop(filename):
    """Determine whether this file is closed loop."""
    try:
        with h5py.File(filename, 'r') as f:
            loop = f['telemetry']['slopes'].attrs.get("LOOPSTATE", "??")
            return loop in (1, "Closed")
    except Exception as e:
        print("Exception {0} for file {1}".format(type(e), filename))
        return None

@task
@hosts("localhost")
def ql(date=None, force=False):
    """Quick look telemetry. Assume open loop follows closed loop."""
    date = parse_dt(date)
    force = parse_bool(force)
    telroot = sep + pjoin("Volumes","LaCie","Telemetry2","ShaneAO", "{0:%Y-%m-%d}".format(date)) + sep
    cmdroot = os.path.dirname(os.path.dirname(__file__))
    outroot = os.path.expanduser("~/Development/ShaneAO/ShWLSimulator")

    cmd = pjoin(cmdroot, 'analysis', 'tql.py')
    cl, ol = None, None
    for fn in iglob(pjoin(telroot, 'telemetry_*.hdf5')):
        m = re.match(r'telemetry_([\d]+)\.hdf5', os.path.basename(fn))
        if not m:
            print("Filename {0} seems wrong.".format(fn))
            continue
        n = int(m.group(1))
        closed = is_closed_loop(fn)
        if closed is None:
            continue
        if closed:
            cl = n
            ol = None
        else:
            ol = n
        if cl is not None and ol is not None:
            directory = os.path.exists(pjoin(outroot, "{0:%Y-%m-%d}".format(date), "C{0:04d}-O{1:04d}".format(cl, ol)))
            if (not directory) or force:
                local("{0} {cl:d} {ol:d}".format(cmd, cl=cl, ol=ol))
            cl = None
    

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
