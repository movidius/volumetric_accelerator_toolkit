#!/usr/bin/env python3
"""
Las2vola: Converts Las files into VOLA format.

The ISPRS las format is the standard for LIDAR devices and stores information
on the points obtained. This parser uses the las information
for the nbit per voxel representation. The data stored is: color, height,
number of returns, intensity and classification
@author Jonathan Byrne & Anton Shmatov
@copyright 2018 Intel Ltd (see LICENSE file).
"""
from __future__ import print_function
import glob
import os
import numpy as np
import binutils as bu
from laspy import file as lasfile
from laspy.util import LaspyException
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

            bu.print_ratio(filename, outfilename)
        else:
            print("The las file is empty!")
    bu.timer(start_time)


def parse_las(filename, nbits):
    """Read las format point data and return header and points."""
    pointfile = lasfile.File(filename, mode='r')
    header = pointfile.header
    maxheight = header.max[2]
    points = np.array((pointfile.x, pointfile.y, pointfile.z)).transpose() # get all points, change matrix orientation
    pointsdata = np.zeros((len(pointfile), 7), dtype=np.int)

    if nbits > 0: # if want to set other data, find in matrices
        try:
            red = pointfile.red
        except LaspyException:
            red = [0] * len(points)

        try:
            green = pointfile.green
        except LaspyException:
            green = [0] * len(points)

        try:
            blue = pointfile.blue
        except LaspyException:
            blue = [0] * len(points)

        coldata = np.int64(np.array([red, green, blue]).transpose() / 256)
        scaleddata = np.array([pointfile.get_z(), pointfile.get_num_returns(), 
            pointfile.intensity, pointfile.raw_classification], dtype='int64').transpose()

        min = np.array([0, 1, 0, 0])
        max = np.array([maxheight, 7, 1000, 31])
        normdata = np.int64(bu.normalize_np(scaleddata, min, max) * 255)

        coldata[(coldata[:, 0] == 0) & (coldata[:, 1] == 0) &
            (coldata[:, 2] == 0)] = 200 # if all three colours are 0, set to 200

        pointsdata = np.concatenate([coldata, normdata], axis=1)

    if len(points) == 0:
        return [], [], None

    bbox = [points.min(axis=0).tolist(), points.max(axis=0).tolist()]

    if nbits:
        return bbox, points, pointsdata
    else:
        return bbox, points, None


if __name__ == '__main__':
    main()
