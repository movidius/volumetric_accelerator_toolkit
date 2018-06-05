#!/usr/bin/env python3
"""
Converts stl triangle meshes into VOLA format.

STL is an industry standard mesh format. There is no information other than
triangles so the occupancy information is only available for this format.

@author Jonathan Byrne
@copyright 2018 Intel Ltd (see LICENSE file).
"""
#TODO: Need to cleverly remove duplicate points and add subdivide function.
from __future__ import print_function
import glob
import os
import numpy as np
from stl import mesh
import binutils as bu
from volatree import VolaTree


def main():
    """Read the file, build the tree. Write a Binary."""
    start_time = bu.timer()
    parser = bu.parser_args("*.stl")
    parser = bu.add_reverse(parser)
    args = parser.parse_args()

    # Parse directories or filenames, whichever you want!
    if os.path.isdir(args.input):
        filenames = glob.glob(os.path.join(args.input, '*.stl'))
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
        bbox, points = parse_stl(filename, revzy=args.reverse_zy)

        if args.reverse_zy:
            points = np.array([points[:, 0], points[:, 2], points[:, 1]]).transpose()

        print("STL only has occupancy data," +
              " no additional data is being added")
        nbits = 0

        volatree = VolaTree(args.depth, bbox, args.crs, args.dense, nbits)
        volatree.cubify(points)
        volatree.countlevels()
        volatree.writebin(outfilename)

        bu.print_ratio(filename, outfilename)

    bu.timer(start_time)


def parse_stl(filename, revzy=False):
    """Read stl format mesh and return header and points."""
    stlmesh = mesh.Mesh.from_file(filename)
    minvals = stlmesh.min_.tolist()
    maxvals = stlmesh.max_.tolist()
    bbox = [minvals, maxvals]
    points = stlmesh.points[:, :3]
    points = np.append(points, stlmesh.points[:, 3:6], axis=0)
    points = np.append(points, stlmesh.points[:, 6:], axis=0)

    return bbox, points


if __name__ == '__main__':
    main()
