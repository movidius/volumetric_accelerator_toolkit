#!/usr/bin/env python3
"""
Converts bin files from the kitti dataset into VOLA format.

Kitti is a LIDAR dataset for automotive testing. The dataset
stores an intensity value which is converted to a greyscale
color for nbits VOLA.
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
    parser = bu.parser_args("*.bin")
    args = parser.parse_args()

    # Parse directories or filenames, whichever you want!
    if os.path.isdir(args.input):
        filenames = glob.glob(os.path.join(args.input, '*.bin'))
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
        bbox, points, pointsdata = parse_bin(filename, args.nbits)

        # work out how many chunks are required for the data
        if args.nbits:
            print("nbits set, adding metadata to occupancy grid")
            div, mod = divmod(len(pointsdata[0]), 8)
            if mod > 0:
                nbits = div + 1
            else:
                nbits = div
        else:
            print("Only occupancy data being set! Use -n flag to add metadata")
            nbits = 0

        if len(points) > 0:
            volatree = VolaTree(args.depth, bbox, args.crs,
                                args.dense, nbits)
            volatree.cubify(points, pointsdata)
            volatree.countlevels()
            volatree.writebin(outfilename)

            bu.print_ratio(filename, outfilename)
        else:
            print("The las file is empty!")
    bu.timer(start_time)


def parse_bin(filename, nbits):
    """Read in float values and reshape to 2d numpy array."""
    scan = np.fromfile(filename, dtype=np.float32)
    data = scan.reshape((-1, 4))
    points = data[:, :3]
    minvals = points.min(axis=0).tolist()
    maxvals = points.max(axis=0).tolist()
    bbox = [minvals, maxvals]

    if nbits:
        pointsdata = data[:, 3:]
        # All values are nonzero otherwise they wont render
        for x in np.nditer(pointsdata, op_flags=['readwrite']):
            x[...] = bu.normalize(x, -.2, 1)
        pointsdata = np.repeat(pointsdata, 3, axis=1)
        pointsdata = np.multiply(pointsdata, 255).astype(int)
        return bbox, points, pointsdata
    else:
        return bbox, points, None


if __name__ == '__main__':
    main()
