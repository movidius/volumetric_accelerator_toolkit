#!/usr/bin/env python3
"""Reads all the headers in a folder and creates a vola index.
@author Jonathan Byrne
@copyright 2018 Intel Ltd (see LICENSE file).
"""
from __future__ import print_function
import argparse
import glob
import os
import struct
import json


def main():
    """Read the headers, calc the centroids and output."""
    parser = argparse.ArgumentParser()
    parser.add_argument("pathname",
                        help="the path containing volume files", type=str)
    args = parser.parse_args()
    dirname = args.pathname.rstrip('/')
    dataset = os.path.basename(dirname)
    volaname = os.path.join(dirname, dataset) + ".vola"
    vol = os.path.join(dirname, "*.vol")
    infofile = os.path.join(dirname, "info.json")

    print("Processing folder:", dirname, " output:", volaname)

    files = []
    tminx, tminy, tminz = float('inf'), float('inf'), float('inf')
    tmaxx, tmaxy, tmaxz = float('-inf'), float('-inf'), float('-inf')

    filenames = glob.glob(vol)
    hdr = {}
    for filename in filenames:
        with open(filename, "rb") as f:
            hdr['headersize'] = struct.unpack('I', f.read(4))[0]
            hdr['version'] = struct.unpack('H', f.read(2))[0]
            hdr['mode'] = struct.unpack('B', f.read(1))[0]
            hdr['depth'] = struct.unpack('B', f.read(1))[0]
            hdr['nbits'] = struct.unpack('I', f.read(4))[0]
            hdr['crs'] = struct.unpack('I', f.read(4))[0]
            hdr['lat'] = struct.unpack('d', f.read(8))[0]
            hdr['lon'] = struct.unpack('d', f.read(8))[0]
            minx = struct.unpack('d', f.read(8))[0]
            miny = struct.unpack('d', f.read(8))[0]
            minz = struct.unpack('d', f.read(8))[0]
            maxx = struct.unpack('d', f.read(8))[0]
            maxy = struct.unpack('d', f.read(8))[0]
            maxz = struct.unpack('d', f.read(8))[0]

        if minx < tminx:
            tminx = minx
        if miny < tminy:
            tminy = miny
        if minz < tminz:
            tminz = minz

        if maxx > tmaxx:
            tmaxx = maxx
        if maxy > tmaxy:
            tmaxy = maxy
        if maxz > tmaxz:
            tmaxz = maxz

        bbox = [minx, miny, minz, maxx, maxy, maxz]
        sides = [maxx - minx, maxy - miny, maxz - minz]
        centroid = ((minx + maxx) / 2, (miny + maxy) / 2, (minz + maxz) / 2)

        files.append({
            'filename': filename,
            'bbox': bbox,
            'centroid': centroid,
            'sides': sides,
            'crs': hdr['crs'],
            'lat': hdr['lat'],
            'lon': hdr['lon']
        })

    if not os.path.isfile(infofile):
        print("Missing attribution info file!! Attribution is required")
        exit()
    else:
        with open(infofile) as data_file:
            infodata = json.load(data_file)
            if len(infodata['license']) < 5:
                print("No license information!! License is required")
                exit()

    vola = {}
    print("Depth:", hdr['depth'])
    vola['dataset'] = infodata['dataset']
    vola['info'] = infodata['info']
    vola['url'] = infodata['url']
    vola['author'] = infodata['author']
    vola['authorurl'] = infodata['authorurl']
    vola['license'] = infodata['license']
    vola['licenseurl'] = infodata['licenseurl']
    vola['files'] = files
    vola['depth'] = hdr['depth']
    vola['nbits'] = hdr['nbits']
    vola['crs'] = hdr['crs']
    vola['mode'] = hdr['mode']
    vola['bbox'] = [tminx, tminy, tminz, tmaxx, tmaxy, tmaxz]
    vola['sides'] = [tmaxx - tminx, tmaxy - tminy, tmaxz - tminz]
    vola['centroid'] = ((tminx + tmaxx) / 2, (tminy + tmaxy) / 2,
                        (tminz + tmaxz) / 2)

    volafile = open(volaname, 'w')
    volafile.write(json.dumps(vola, sort_keys=True, indent=2))
    volafile.close()


if __name__ == '__main__':
    main()
