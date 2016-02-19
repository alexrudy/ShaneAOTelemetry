#!/usr/bin/env bash
./scripts/read.py ~/Documents/Telemetry/ShaneAO/2016-01-22/
./scripts/sequence.py
./scripts/make.py coefficients
./scripts/make.py periodograms
./scripts/make.py tf
./scripts/make.py tffit coefficients