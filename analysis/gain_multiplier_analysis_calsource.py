#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
An analysis of the gain multiplier effect.
"""

import sys, argparse, glob, os
from gain_multiplier_analysis import *
from sqlalchemy import or_

def generate_table(query_base, eliminate):
    """Generate a table from a query base."""
    from astropy.table import Table
    from telemetry.ext.shaneao.models import ShaneAOInfo
    from telemetry.models import Dataset
    
    query_default = query_base.filter(ShaneAOInfo.ngs_matrix == "controlMatrix_16x.fits").filter(
                                      Dataset.date.between(datetime.date(2016, 01, 22), datetime.date(2016, 01, 24)))
    query_midrange = query_base.filter(ShaneAOInfo.ngs_matrix == "controlMatrix_16x.incgain.250Hz.fits").filter(
                                       Dataset.date.between(datetime.date(2016, 03, 16), datetime.date(2016, 03, 17)))
    data = Table(list(itertools.chain(
        gather_query(query_default, 1.0, eliminate), gather_query(query_midrange, 4.0, eliminate))))
    return data

def main():
    """Main function."""
    parser = argparse.ArgumentParser()
    opt = parser.parse_args()
    
    # Handle imports
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams['text.usetex'] = False
    import seaborn as sns
    from telemetry.application import app
    from telemetry.models import Dataset, TelemetryKind, Instrument, Telemetry
    from telemetry.ext.shaneao.models import ShaneAOInfo
    
    # GAIN_MULTIPLIER = 4.0
    # ELIMINTATE = [396, 405, 366]
    ELIMINTATE = []
    root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    OUTPUT_DIRECTORY = os.path.join(root, "gain_trends", "calsource")
    COMPONENT = 'hcoefficients'
    component_name_transform = "transferfunctionmodel/{0}".format
    
    with app.app_context():
        kind = TelemetryKind.require(app.session, component_name_transform(COMPONENT))
        query = app.session.query(Telemetry).join(Dataset).join(Instrument).filter(Instrument.name == 'ShaneAO')
        query = query.join(Telemetry.kind).filter(TelemetryKind.id == kind.id)
        query = query.join(Dataset.instrument_data).join(ShaneAOInfo)
        data = generate_table(query, ELIMINTATE)
        print(data['boost'])
        data.write(os.path.join(OUTPUT_DIRECTORY,"gain_trends.txt"), format='ascii.fixed_width')
        analyze_table(data, OUTPUT_DIRECTORY)
        data['fit gain'].format = "{:.3f}"
        data['fit sigma'].format = "{:.3f}"

if __name__ == '__main__':
    main()