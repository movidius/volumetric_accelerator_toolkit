"""
Filter a vola file by value and then set a color and write the file.
@author Jonathan Byrne
@copyright 2018 Intel Ltd (see LICENSE file).
"""
import argparse
import numpy as np
import binutils as bu
import volareader as vr


def main():
    """Read file, filter and output."""
    parser = argparse.ArgumentParser()
    parser.add_argument("vol",
                        help="the name of the vola file to open",
                        type=str)

    args = parser.parse_args()

    header, levels, data = vr.open_file(args.vol)
    voxels, voxel_data = vr.get_voxels(header, levels, data)
    coords = vr.get_coords(header, voxels)
    filter_voxels(header, coords, voxel_data)


def filter_voxels(header, coords, voxel_data):
    """The returns are byte 5. Setting the color to green."""
    filtered_data = np.zeros((len(voxel_data), 8), dtype=np.int)
    filtered = False
    for idx, data in enumerate(voxel_data):
        bytevals = bu.get_byte_array(data)
        if bytevals[4] > 50:
            filtered = True
            bytevals[0] = 0
            bytevals[1] = 240
            bytevals[2] = 0
        filtered_data[idx] = bytevals
    filename = header['filename'].replace('.vol', '_filtered.vol')
    if not filtered:
        print("Nothing was filtered!")
        exit()
    print("Saving filtered file:", filename)
    vr.save_file(filename, header, coords, filtered_data)


if __name__ == '__main__':
    main()
