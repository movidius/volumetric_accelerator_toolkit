#!/usr/bin/env python3
"""
Reads data from ESRI ascii Grids
@deprecated This has not been used since version 0.9
@author Jonathan Byrne & Anton Shmatov
@copyright 2018 Intel Ltd (see LICENSE file).
"""
from __future__ import print_function
from collections import namedtuple
import sys
import glob
import pyproj
from volatree import VolaTree


def main(filestring, depth):
    """Read the file, build the tree. Write a Binary."""
    for filename in glob.glob(filestring):
        outfilename = filename.replace('aaigrid', 'vol')

        print("converting", filename, "to", outfilename)
        header = parse_grid_header(filename)
        bbox = [header['min'], header['max']]
        data = parse_grid_data(filename, header)
        volatree = VolaTree(depth, bbox, 2000, False, 0)
        volatree.cubify(data)
        volatree.writebin(outfilename)

        bu.print_ratio(filename, outfilename)
        # volatree.printlevel(depth, True)


def parse_grid_header(filename):
    """Read ESRI Grid format point data and return header and points."""
    infile = open(filename, 'r')
    header = {}

    ncols = int(infile.readline().split()[1])
    nrows = int(infile.readline().split()[1])
    xllcorner = float(infile.readline().split()[1])
    yllcorner = float(infile.readline().split()[1])
    cellsize = float(infile.readline().split()[1])

    maxx = xllcorner + (ncols * cellsize)
    maxy = yllcorner + (nrows * cellsize)
    header['min'] = [xllcorner, yllcorner, 0]
    header['max'] = [maxx, maxy, 1000]
    header['rows'] = nrows
    header['cols'] = ncols
    header['cellsize'] = cellsize
    return header


def parse_grid_data(filename, header, lasout=False):
    """Turning the grid into points for standardised interface."""
    itm = pyproj.Proj(init='epsg:2157')
    # irishgrid = pyproj.Proj(init='epsg:29902')
    wgs84 = pyproj.Proj(init='epsg:4326')

    infile = open(filename, 'r')
    data = []
    minz = float("inf")
    maxz = float("-inf")
    linecnt = 0
    point = namedtuple('Point', 'x y z')
    minx = header['min'][0]
    miny = header['min'][1]
    csize = header['cellsize']

    # Ignore the header
    line = infile.readline()
    while len(line) < 40:
        line = infile.readline()

    if lasout:
        outfilename = filename.replace('aaigrid', 'xyz')
        outfile = open(outfilename, 'w')

    for line in infile:
        linecnt += 1
        print("processing row", linecnt)

        line = line.rstrip()
        row = [int(x) for x in line.split()]
        rowmax = max(row)
        rowmin = min(row)

        if rowmax > maxz:
            maxz = rowmax
        if rowmin < minz:
            minz = rowmin

        for idx, z in enumerate(row):
            x = minx + (csize * idx)
            y = miny + (csize * (header['rows'] - linecnt))
            transform = pyproj.transform(wgs84, itm, x, y)
            if lasout:
                outfile.write(
                    str(transform[0]) + ' ' + str(transform[1]) + ' ' + str(z)
                    + '\n')
            data.append(point(x=transform[0], y=transform[1], z=z))

    reproj = pyproj.transform(wgs84, itm, header['min'][0], header['min'][1])
    header['min'][0] = reproj[0]
    header['min'][1] = reproj[1]
    header['min'][2] = minz

    reproj = pyproj.transform(wgs84, itm, header['max'][0], header['max'][1])
    header['max'][0] = reproj[0]
    header['max'][1] = reproj[1]
    header['max'][2] = maxz

    if lasout:
        print("writing file:", outfilename)
        outfile.close()
    return data


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage %s <filename> <treedepth>" % sys.argv[0])
        exit()
    main(sys.argv[1], int(sys.argv[2]))
