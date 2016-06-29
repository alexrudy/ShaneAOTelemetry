#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
An analysis of the gain multiplier effect.
"""

import sys, argparse, glob, os
from gain_multiplier_analysis import *
from sqlalchemy import or_
from astropy.table import Table

def main():
    """Main function."""
    parser = argparse.ArgumentParser()
    opt = parser.parse_args()
    
    # Handle imports
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams['text.usetex'] = False
    import seaborn as sns
    
    # GAIN_MULTIPLIER = 4.0
    # ELIMINTATE = [396, 405, 366]
    ELIMINTATE = []
    root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    OUTPUT_DIRECTORY = os.path.join(root, "gain_trends", "calsource")
    COMPONENT = 'hcoefficients'
    component_name_transform = "transferfunctionmodel/{0}".format
    
    data = Table.read(os.path.join(OUTPUT_DIRECTORY,"gain_trends.txt"), format='ascii.fixed_width')
    data['gain'] = data['effective gain'] / data['boost']
    analyze_table(data, OUTPUT_DIRECTORY)
    data['fit gain'].format = "{:.3f}"
    data['fit sigma'].format = "{:.3f}"

if __name__ == '__main__':
    main()