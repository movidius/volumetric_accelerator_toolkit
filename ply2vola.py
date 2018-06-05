#!/usr/bin/env python3
"""
Converts ply triangle meshes into VOLA format.

PLY is an industry standard mesh format. This parser only looks at the points
and their colors, not the triangles.

@author Jonathan Byrne
@copyright 2018 Intel Ltd (see LICENSE file).
"""
#TODO: Need to cleverly remove duplicate points and add subdivide function.
from __future__ import print_function
import glob
import os
import plyfile
import numpy as np
from stl import mesh
import binutils as bu
from volatree import VolaTree


def main():
    """Read the file, build the tree. Write a Binary."""
    start_time = bu.timer()
    parser = bu.parser_args("*.ply")
    parser = bu.add_reverse(parser)
    args = parser.parse_args()

    # Parse directories or filenames, whichever you want!
    if os.path.isdir(args.input):
        filenames = glob.glob(os.path.join(args.input, '*.ply'))
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
        bbox, points, pointsdata = parse_ply(filename, args.nbits)

        if args.reverse_zy:
            points = np.array([points[:, 0], points[:, 2], points[:, 1]]).transpose()

        # work out how many chunks are required for the data
        print("PLY only has occupancy data," +
              " no additional data is being added")
        nbits = 0

        volatree = VolaTree(args.depth, bbox, args.crs, args.dense, nbits)
        volatree.cubify(points)
        volatree.countlevels()
        volatree.writebin(outfilename)

        bu.print_ratio(filename, outfilename)

    bu.timer(start_time)


def parse_ply(filename, nbits):
    """Read ply format mesh and return header and points."""
    ply_file = plyfile.PlyData.read(filename)
    vertices = ply_file.elements[0].data
    coords = np.zeros((len(vertices), 3), dtype=np.float)

    for idx, vert in enumerate(vertices):
        coords[idx] = list(vert)[:3]

    minvals = coords.min(axis=0).tolist()
    maxvals = coords.max(axis=0).tolist()
    bbox = [minvals, maxvals]

    return bbox, coords, None


if __name__ == '__main__':
    main()
