#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
txt2vola: Converts xyz point clouds into VOLA format.
ASSUMPTION: first line is header from pdal
This will automatically parse files with a structure
x, y, z, intensity, r, g, b, classification

@author Ananya Gupta and Jonathan Byrne
@copyright 2018 Intel Ltd (see LICENSE file).
"""

from __future__ import print_function
import glob
import os
import numpy as np
import binutils as bu
from volatree import VolaTree


def main():
    """Read the file, build the tree. Write a Binary."""
    start_time = bu.timer()
    parser = bu.parser_args("*.asc / *.xyz")
    args = parser.parse_args()

    # Parse directories or filenames, whichever you want!
    if os.path.isdir(args.input):
        filenames = glob.glob(os.path.join(args.input, '*.txt'))
        filenames.extend(glob.glob(os.path.join(args.input, '*.asc')))
    else:
        filenames = glob.glob(args.input)

    print("processing: ", ' '.join(filenames))
    for filename in filenames:
        if args.dense:
            outfilename = bu.sub(filename, "dvol")
        else:
            outfilename = bu.sub(filename, "vol")
        if os.path.isfile(outfilename):
            print("File already exists!")
            continue

        print("converting", filename, "to", outfilename)
        bbox, points, pointsdata = parse_xyz(filename, args.nbits)
        # work out how many chunks are required for the data
        if args.nbits:
            div, mod = divmod(len(pointsdata[0]), 8)
            if mod > 0:
                nbits = div + 1
            else:
                nbits = div
        else:
            nbits = 0

        if len(points) > 0:
            volatree = VolaTree(args.depth, bbox, args.crs,
                                args.dense, nbits)
            volatree.cubify(points, pointsdata)
            volatree.countlevels()
            volatree.writebin(outfilename)

            bu.print_ratio(filename, outfilename)
        else:
            print("The points file is empty!")
    bu.timer(start_time)


def parse_xyz(filename, nbits):
    """Read xyz format point data and return header, points and points data."""
    pointstrings = []
    with open(filename) as points_file:
        next(points_file)
        for line in points_file:
            if not line.startswith('#'):
                if not line.isspace():
                    line = line.replace(',', ' ')
                    line = line.split()
                    pointstrings.append(line)

    points = np.zeros((len(pointstrings), 3), dtype=np.float)
    if nbits > 0:
        datalen = len(pointstrings[0][3:])
        pointsdata = np.zeros((len(pointstrings), datalen), dtype=np.int)

    for idx, line in enumerate(pointstrings):
        coords = line[: 3]
        coords = [float(i) for i in coords]
        points[idx] = coords
        if nbits > 0:
            data = line[3:]
            data = [int(float(i)) for i in data]
            data[0] = int(bu.normalize(data[0], -1500, 0) * 255)
            pointsdata[idx] = data

    minvals = points.min(axis=0).tolist()
    maxvals = points.max(axis=0).tolist()
    bbox = [minvals, maxvals]

    if nbits > 0:
        return bbox, points, pointsdata
    else:
        return bbox, points, None


if __name__ == '__main__':
    main()
