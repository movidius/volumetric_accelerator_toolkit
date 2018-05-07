#!/bin/bash

PROCS=1
DEPTH=3
CRS=2905

mkdir pdalfiltered

find . -maxdepth 1 -name "*.laz" | xargs -n1 -P$PROCS -I fname sh -c 'echo fname; pdal -v 4 pipeline noisefilter.json --writers.las.filename=pdalfiltered/fname --readers.las.filename=fname'

cd pdalfiltered
mv ../*.py .
find . -maxdepth 1 -name "*.laz" | xargs -n1 -P$PROCS -I fname python3 las2vola.py fname $DEPTH --crs $CRS -n

