"""
Binary Utilities Class.

Selection of utility functions for binary operations and other handy functions.
"""
from __future__ import print_function
import time
import argparse
import numpy as np
from os.path import splitext

def normalize(val, minval, maxval):
    """Scale a value between 0 and 1."""
    if val >= maxval:
        return 1
    elif val <= minval:
        return 0
    normed = float(val - minval) / float(maxval - minval)
    return normed

def normalize_np(vals, minval, maxval):
    """Scale values within a numpy array between 0 and 1."""
#    vals[vals >= maxval] = 1
#    vals[vals <= minval] = 0

    normed  = np.float64(vals - minval) / np.float64(maxval - minval)

    normed[normed < 0] = 0
    normed[normed > 1] = 1

    return normed

def set_bit(bit64, index):
    """Set bit index on 64 bit unsigned integer to one."""
    bit64 |= np.uint64(1) << np.uint64(index)
    return bit64


def unset_bit(bit64, index):
    """Set bit index on 64 bit unsigned integer to zero."""
    bit64 &= ~(np.uint64(1) << np.uint64(index))
    return bit64


def flip_bit(bit64, index):
    """Set bit index on 64 bit unsigned integer to opposite of what it was."""
    bit64 ^= np.uint64(1) << np.uint64(index)
    return bit64


def read_bit(bit64, index):
    """Pull the value at bit index."""
    bit = (int(bit64) >> index) & 1
    return bit


def count_bits(vol):
    """Count all bits set to 1."""
    count = 0
    vol = np.uint64(vol)
    for i in range(64):
        bit = read_bit(vol, i)
        if bit == 1:
            count += 1
    return count


def count_neighbours(target, mask):
    """Use a mask to calculate the bit occupancy of the surrounding pixels."""
    result = target & mask
    neighbours = count_bits(result)
    masksize = count_bits(mask)
    return neighbours, masksize


def print_binary(np64):
    """Print as string with all the zeros."""
    print("{0:064b}".format(np64))


def get_indexes(vol):
    """Return all the indices in a given vol."""
    indices = []
    vol = np.uint64(vol)
    for i in range(64):
        bit = read_bit(vol, i)
        if bit == 1:
            indices.append(i)
    return indices


def get_byte_array(intval):
    """Generate byte array from numpy integer."""
    byte_array = [int(i) for i in intval.tobytes()]
    return byte_array


def xyz_from_sparse_index(indexes):
    """Generate coordinates from sparse index."""
    x, y, z, = 0, 0, 0
    for level, index in enumerate(indexes):
        mult = pow(4, ((len(indexes) - 1) - level))
        x += (index % 4) * mult
        y += (index % 16 // 4) * mult
        z += (index // 16) * mult
    return (x, y, z)


def sparse_indexes(coord, depth):
    """Generate sparse indexes from coordinate."""
    indexes = [0] * depth
    x = coord[0]
    y = coord[1]
    z = coord[2]

    for i in range(depth):
        divx, modx = divmod(x, 4)
        divy, mody = divmod(y, 4)
        divz, modz = divmod(z, 4)
        index = modx + (mody * 4) + (modz * 16)
        level = (depth - i) - 1
        indexes[level] = index

        x = divx
        y = divy
        z = divz

    return indexes


def timer(starttime=None):
    """Generate timing information in h,m,s format."""
    if starttime is None:
        return time.time()
    else:
        endtime = time.time()
        seconds = endtime - starttime
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        print("Time Taken: %d:%02d:%02d" % (h, m, s))
        return endtime


def parser_args(wildcards):
    """Default parser arguments, all in one handy place."""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "input",
        help="the name of the file / files / directory you want to open.\
              You can used wildcards(" + wildcards + ") or the directory\
              for multiple files. Make sure you put it in quotation marks\
              otherwise linux will expand it e.g.: xyz2vola \"*.laz\"",
        type=str)

    parser.add_argument(
        "depth", help="how many levels the vola tree will use", type=int)

    parser.add_argument(
        "--crs",
        help="the coordinate system of the input, e.g.,\
              29902 (irish grid epsg code)",
        type=int, default=2000)

    parser.add_argument(
        "-n",
        "--nbits",
        help="use 1+nbits per voxel. The parser works out what info to embed",
        action='store_true')

    parser.add_argument(
        "-d",
        "--dense",
        help="output a dense point cloud",
        action='store_true')
    return parser

# replacement for re.sub that only modifies the extension
def sub(filepath, new_ext):
    bare_file = splitext(filepath)[0]

    if '.' in new_ext:
        return bare_file + new_ext
    else:
        return bare_file + '.' + new_ext
