#!/usr/bin/env python3
"""
pcd2vola: Converts ascii PCL point clouds into VOLA format.

This will automatically parse files with a structure x,y, z or
x, y, z, r, g, b, intensity
@author Jonathan Byrne
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
    parser = bu.parser_args("*.pcd")
    args = parser.parse_args()

    # Parse directories or filenames, whichever you want!
    if os.path.isdir(args.input):
        filenames = glob.glob(os.path.join(args.input, '*.pcd'))
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
        bbox, points, pointsdata = parse_pcd(filename, args.nbits)
        print("PCD only has occupancy data," +
              " no additional data is being added")

        if len(points) > 0:
            volatree = VolaTree(args.depth, bbox, args.crs,
                                args.dense, 0)
            volatree.cubify(points, pointsdata)
            volatree.countlevels()
            volatree.writebin(outfilename)
        else:
            print("The points file is empty!")
    bu.timer(start_time)


def parse_pcd(filename, nbits):
    """Read xyz format point data and return header, points and points data."""
    pointstrings = []
    header = True
    with open(filename) as points_file:
        while header:
            line = points_file.readline()
            if line.startswith('DATA'):
                line = line.rstrip()
                line = line.split(' ')
                print(line[1])
                if line[1] == 'ascii':
                    header = False
                else:
                    print("pcd2vola only handles ascii files!!!")
                    exit()

        for line in points_file:
            if not line.startswith('nan'):
                if not line.isspace():
                    line = line.split()
                    pointstrings.append(line)

    points = np.zeros((len(pointstrings), 3), dtype=np.float)
    # if nbits > 0:
    #     datalen = len(pointstrings[0][3:])
    #     pointsdata = np.zeros((len(pointstrings), datalen), dtype=np.int)

    for idx, line in enumerate(pointstrings):
        coords = line[: 3]
        coords = [float(i) for i in coords]
        points[idx] = coords
        # if nbits > 0:
        #     data = line[3:]
        #     data = [int(i) for i in data]
        #     pointsdata[idx] = data

    minvals = points.min(axis=0).tolist()
    maxvals = points.max(axis=0).tolist()
    bbox = [minvals, maxvals]

    # if nbits > 0:
    #     return bbox, points, pointsdata
    # else:
    return bbox, points, None


if __name__ == '__main__':
    main()
