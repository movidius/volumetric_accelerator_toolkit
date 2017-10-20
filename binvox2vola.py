#!/usr/bin/env python3
"""
xyz2vola: Converts binvox files into VOLA format.

Binvox is a very popular volumetric representation that uses run
length encoding to achieve significant compression. It is included
as there are many datasets that are stored in binvox format.
There is no information other than voxels so the occupancy information
is only available for this format.

TODO: switch xyz and xzy encoding
@author Jonathan Byrne
"""
from __future__ import print_function
import glob
import re
import os
import numpy as np
import binutils as bu
from volatree import VolaTree


def main():
    """Read the file, build the tree. Write a Binary."""
    start_time = bu.timer()
    parser = bu.parser_args("*.binvox")
    args = parser.parse_args()

    # Parse directories or filenames, whichever you want!
    if os.path.isdir(args.input):
        filenames = glob.glob(os.path.join(args.input, '*.binvox'))
    else:
        filenames = glob.glob(args.input)

    print("processing: ", ' '.join(filenames))
    for filename in filenames:
        if args.dense:
            outfilename = re.sub("(?i)binvox", "dvol", filename)
        else:
            outfilename = re.sub("(?i)binvox", "vol", filename)
        if os.path.isfile(outfilename):
            print("File already exists!")
            continue

        print("converting", filename, "to", outfilename)
        bbox, points, pointsdata = parse_binvox(filename)

        if args.nbits:
            print("binvox only has occupancy data!")
        nbits = 0

        if len(points) > 0:
            volatree = VolaTree(args.depth, bbox, args.crs,
                                args.dense, nbits)
            volatree.cubify(points, pointsdata)
            volatree.writebin(outfilename)
        else:
            print("The points file is empty!")
    bu.timer(start_time)


def parse_binvox(filename):
    """Read xyz format point data and return header, points and points data."""
    header = {}
    with open(filename, 'rb') as infile:
        # read header info
        line = infile.readline().strip()
        if line.startswith(b'#binvox'):
            header['dims'] = [int(x) for x in
                              infile.readline().strip().split(b' ')[1:]]
            header['translate'] = [float(x) for x in
                                   infile.readline().strip().split(b' ')[1:]]
            header['scale'] = float(infile.readline().strip().split(b' ')[1])
            infile.readline()  # to remove the data line
        else:
            print("Not a binvox file")
            exit()
        bytevals = np.frombuffer(infile.read(), dtype=np.uint8)

    points = runlength_to_xyz(bytevals, header)
    # show everything
    # np.set_printoptions(threshold=np.inf)
    # supress scientific notation
    np.set_printoptions(suppress=True)
    minvals = points.min(axis=0).tolist()
    maxvals = points.max(axis=0).tolist()

    if header['dims'][0] == 32:
        maxvals = [64, 64, 64]
    elif header['dims'][0] == 128:
        maxvals = [256, 256, 256]
    elif header['dims'][0] == 512:
        maxvals = [1024, 1024, 1024]
    else:
        maxvals = header['dims']
    bbox = [minvals, maxvals]
    return bbox, points, None


def runlength_to_xyz(bytevals, header):
    """Binvox uses a binary runlength encoding (valuebyte, countbyte)."""
    # odds and evens, the value and then the count is specified
    values, counts = bytevals[::2], bytevals[1::2]

    # Make a list of start/end indexes for each run.
    start, end = 0, 0
    end_indexes = np.cumsum(counts)
    indexes = np.concatenate(([0], end_indexes[:-1])).astype(np.int)

    # use the values as booleans to remove empty points from the array
    values = values.astype(np.bool)
    indexes = indexes[values]
    end_indexes = end_indexes[values]

    occupied_voxels = []
    for start, end in zip(indexes, end_indexes):
        occupied_voxels.extend(range(start, end))
    occupied_voxels = np.array(occupied_voxels)

    x = occupied_voxels / (header['dims'][0]*header['dims'][1])
    zwpy = occupied_voxels % (header['dims'][0]*header['dims'][1])  # z*w + y
    z = zwpy / header['dims'][0]
    y = zwpy % header['dims'][0]
    points = np.vstack((x, y, z)).T
    return points


if __name__ == '__main__':
    main()
