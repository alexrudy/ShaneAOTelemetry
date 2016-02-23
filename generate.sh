#!/usr/bin/env bash
./scripts/read.py ~/Documents/Telemetry/ShaneAO/2016-01-22/raw/
./scripts/sequence.py -q
./scripts/make.py coefficients -f
./scripts/make.py periodograms -f
./scripts/make.py tf -f
./scripts/make.py tffit coefficients