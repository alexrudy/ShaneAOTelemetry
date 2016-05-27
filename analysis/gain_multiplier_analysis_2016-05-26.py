#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
An analysis of the gain multiplier effect.
"""

import sys, argparse, glob, os
from gain_multiplier_analysis import *

def generate_table(query_base, eliminate):
    """Generate a table from a query base."""
    from astropy.table import Table
    from telemetry.ext.shaneao.models import ShaneAOInfo
    
    query_default = query_base.filter(ShaneAOInfo.ngs_matrix == "controlMatrix_16x.fits")    
    query_midrange = query_base.filter(ShaneAOInfo.ngs_matrix == "controlMatrix_16x.incgain.250Hz.fits")
    query_boosted = query_base.filter(ShaneAOInfo.ngs_matrix == "controlMatrix_16x.incgain.1000Hz.fits")
    data = Table(list(itertools.chain(
        gather_query(query_default, 1.0, eliminate), gather_query(query_midrange, 4.0, eliminate),
        gather_query(query_boosted, 20.0, eliminate))))
    return data

def main():
    """Main function."""
    parser = argparse.ArgumentParser()
    opt = parser.parse_args()
    
    # Handle imports
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams['text.usetex'] = False
    from telemetry.application import app
    from telemetry.models import Dataset, TelemetryKind, Instrument, Telemetry
    from telemetry.ext.shaneao.models import ShaneAOInfo
    
    # GAIN_MULTIPLIER = 4.0
    # ELIMINTATE = [396, 405, 366]
    ELIMINTATE = []
    root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    OUTPUT_DIRECTORY = os.path.join(root, "gain_trends", "2016-05-25")
    COMPONENT = 'hcoefficients'
    component_name_transform = "transferfunctionmodel/{0}".format
    
    with app.app_context():
        kind = TelemetryKind.require(app.session, component_name_transform(COMPONENT))
        query = app.session.query(Telemetry).join(Dataset).join(Instrument).filter(Instrument.name == 'ShaneAO')
        query = query.join(Telemetry.kind).filter(TelemetryKind.id == kind.id)
        query = query.filter(Dataset.date.between(datetime.date(2016, 05, 24), datetime.date(2016, 05, 27)))
        query = query.join(Dataset.instrument_data).join(ShaneAOInfo)
        data = generate_table(query, ELIMINTATE)
        analyze_table(data, OUTPUT_DIRECTORY)
        data['fit gain'].format = "{:.3f}"
        data['fit sigma'].format = "{:.3f}"
        data.write(os.path.join(OUTPUT_DIRECTORY,"gain_trends.txt"), format='ascii.fixed_width')

if __name__ == '__main__':
    main()