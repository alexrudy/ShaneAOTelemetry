#!/usr/bin/env bash
./scripts/sequence.py -q
./scripts/make.py hcoefficients -f
./scripts/make.py pseudophase -f
./scripts/make.py phase -f
./scripts/make.py periodograms -f
./scripts/make.py tf -f
./scripts/make.py tffit -f
