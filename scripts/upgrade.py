#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A script for updating ShaneAO unreal telemetry sequences to create
ShadyAO telemetry data sets.
"""

from telemetry.ext.shaneao.sequencer import upgrade

# CLI
import lumberjack
import argparse
import pstats
import cProfile

def main():
    """Main function."""
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=str, help="Path to telemetry data.", nargs="+")
    parser.add_argument("-l", "--limit", type=int, help="Limit the number of files examined.")
    parser.add_argument("-p", "--profile", action='store_true', help="Use a profiler.")
    parser.add_argument("-v", "--verbose", action='store_true', help="Be verbose.")
    parser.add_argument("-q", "--quiet", action='store_true', help="Be verbose.")
    parser.add_argument("-f", "--force", action="store_true", help="Force write new files.")
    opt = parser.parse_args()
    
    if opt.quiet:
        opt.verbose = False
    
    if opt.profile:
        pr = cProfile.Profile()
        pr.enable()
    
    if opt.verbose:
        lumberjack.setup_logging(mode='stream', level=1)
    else:
        lumberjack.setup_logging(mode='stream', level=logging.INFO)
    
    upgrade(opt.path, os.getcwd(), quiet=opt.quiet, verbose=opt.verbose, force=opt.force, limit=opt.limit)
    
    if opt.profile:
        pr.disable()
        sortby = 'cumulative'
        ps = pstats.Stats(pr).sort_stats(sortby)
        ps.print_stats()

if __name__ == '__main__':
    main()