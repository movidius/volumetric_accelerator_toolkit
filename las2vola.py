#!/usr/bin/env python3
"""
Las2vola: Converts Las files into VOLA format.

The ISPRS las format is the standard for LIDAR devices and stores information
on the points obtained. This parser uses the las information
for the nbit per voxel representation. The data stored is: color, height,
number of returns, intensity and classification

@author: Jonathan Byrne
"""
from __future__ import print_function
import glob
import os
import numpy as np
import binutils as bu
from liblas import file as lasfile
from volatree import VolaTree


def main():
    """Read the file, build the tree. Write a Binary."""
    start_time = bu.timer()
    parser = bu.parser_args("*.las / *.laz")
    args = parser.parse_args()

    # Parse directories or filenames, whichever you want!
    if os.path.isdir(args.input):
        filenames = glob.glob(os.path.join(args.input, '*.laz'))
        filenames.extend(glob.glob(os.path.join(args.input, '*.las')))
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
        bbox, points, pointsdata = parse_las(filename, args.nbits)

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
            volatree.writebin(outfilename)
        else:
            print("The las file is empty!")
    bu.timer(start_time)


def parse_las(filename, nbits):
    """Read las format point data and return header and points."""
    pointfile = lasfile.File(filename, mode='r')
    header = pointfile.header
    maxheight = header.max[2]
    points = np.zeros((len(pointfile), 3), dtype=np.float)
    pointsdata = np.zeros((len(pointfile), 7), dtype=np.int)

    for idx, point in enumerate(pointfile):
        points[idx] = [point.x, point.y, point.z]
        if nbits > 0:
            rval = int(bu.normalize(point.number_of_returns, 1, 7) * 255)
            ival = int(bu.normalize(point.intensity, 0, 1000) * 255)
            cval = int(bu.normalize(point.classification, 0, 31) * 255)
            hval = int(bu.normalize(point.z, 0, maxheight) * 255)
            red = int(np.uint16(point.color.red) / 256)
            green = int(np.uint16(point.color.green) / 256)
            blue = int(np.uint16(point.color.blue) / 256)
            if red == green == blue == 0:
                red = green = blue = 200
            pointsdata[idx] = [red, green, blue, hval, rval, ival, cval]
    if len(points) == 0:
        return [], [], None

    bbox = [points.min(axis=0).tolist(), points.max(axis=0).tolist()]

    if nbits:
        return bbox, points, pointsdata
    else:
        return bbox, points, None


if __name__ == '__main__':
    main()
