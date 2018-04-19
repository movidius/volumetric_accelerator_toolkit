"""
VOLA Reader.

Processes sparse vola files (.vol). Reads in the header information and
has a set of functions for extracting the voxel locations and data.
"""
from __future__ import print_function
import struct
import argparse
import os
import numpy as np
import binutils as bu
import random
from volatree import VolaTree


def main():
    """Pull the xyz coordinates of the voxels from the bit array."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "vol",
        help="the name of the vola file to open", type=str)

    parser.add_argument(
        "-d",
        "--header",
        help="print the header detailing information specific to the .vol file",
        action='store_true')

    parser.add_argument(
        "-v",
        "--voxels",
        help="output the positions of the voxels within the VOLA bounding box",
        action='store_true')

    parser.add_argument(
        "-c",
        "--coordinates",
        help="output the coordinates of the voxels within the coordinate\
              reference systems",
        action='store_true')

    parser.add_argument(
        "-g",
        "--get",
        nargs=3,
        help="check if a voxel exists at a given location and return\
             the value if it does. uses the format: -g x y z",
        type=int)

    parser.add_argument(
        "-b",
        "--bincoords",
        help="output the binary coordinates of the voxels in the vola file",
        action='store_true')

    parser.add_argument(
        "-i",
        "--images",
        help="output image planes for each depth",
        action='store_true')

    parser.add_argument(
        "-m",
        "--map",
        help="output flattened map for a given height above the ground",
        type=int,
        default=0)

    parser.add_argument(
        "-n",
        "--numpy",
        help="output the occupancy grid to a numpy array",
        action='store_true')

    args = parser.parse_args()
    header, levels, data = open_file(args.vol)
    voxels, voxel_data = get_voxels(header, levels, data)
    argUsed = False

    if args.voxels:
        argUsed = True
        for vox in voxels:
            print(str(vox)[1:-1])

    if args.coordinates:
        argUsed = True
        coords = get_coords(header, voxels)
        for coord in coords:
            print(str(coord)[1:-1])

    if args.images:
        argUsed = True
        print("writing slices to image folder")
        slice_layers(voxels, header)

    if args.map > 0:
        argUsed = True
        print("generating 2D map")
        generate_map(voxels, header, args.map)

    if args.numpy:
        argUsed = True
        print("generating Numpy Grid")
        numpy_grid(voxels, header)

    if args.bincoords:
        argUsed = True
        bin_coordinates = get_binary_indexes(voxels)
        for (coord, bin_coord) in zip(voxels, bin_coordinates):
            print(str(coord)[1:-1], " ", str(bin_coord))

    if args.get:
        argUsed = True
        get_voxel(args.get, header, levels)

    if args.header:
        argUsed = True
        print_header(header)

    if not argUsed:
        parser.print_help()

def open_file(filename):
    """
    Given a filename, read the header and data.

    Returns header dictionary and two lists.
    """
    header = {}
    with open(filename, "rb") as f:
        header['filename'] = filename
        header['headersize'] = struct.unpack('I', f.read(4))[0]
        header['version'] = struct.unpack('H', f.read(2))[0]
        header['mode'] = struct.unpack('B', f.read(1))[0]
        header['depth'] = struct.unpack('B', f.read(1))[0]
        header['nbits'] = struct.unpack('I', f.read(4))[0]
        header['crs'] = struct.unpack('I', f.read(4))[0]
        header['lat'] = struct.unpack('d', f.read(8))[0]
        header['lon'] = struct.unpack('d', f.read(8))[0]
        header['minx'] = struct.unpack('d', f.read(8))[0]
        header['miny'] = struct.unpack('d', f.read(8))[0]
        header['minz'] = struct.unpack('d', f.read(8))[0]
        header['maxx'] = struct.unpack('d', f.read(8))[0]
        header['maxy'] = struct.unpack('d', f.read(8))[0]
        header['maxz'] = struct.unpack('d', f.read(8))[0]
        header['offset'] = [header['minx'], header['miny'], header['minz']]
        header['sidelength'] = pow(4, header['depth'])
        header['diff'] = [header['maxx'] - header['minx'],
                          header['maxy'] - header['miny'],
                          header['maxz'] - header['minz']]
        header['cubesize'] = max(header['diff']) / header['sidelength']
        # initialise lists for storing levels related data
        levels = []
        data = []
        bitcnt = 1
        # pull in the 64 bit chunks and assign to a level.
        # If using nbits then extract that too!
        for d in range(header['depth']):
            levels.append([])
            newcnt = 0
            for i in range(bitcnt):
                chunk = np.uint64(get_chunk(f))
                newcnt += bu.count_bits(chunk)
                levels[d].append(chunk)
            if header['nbits'] > 0:
                data.append([])
                for i in range(bitcnt):
                    chunk = np.uint64(get_chunk(f))
                    data[d].append(chunk)
            bitcnt = newcnt

    return header, levels, data


def print_header(header):
    """Print the data contained in the header."""
    print("headersize", header['headersize'])
    print("version", header['version'])
    print("mode", header['mode'])
    print("treedepth", header['depth'])
    print("1+nbits:", header['nbits'])
    print("coordinate reference system", header['crs'])
    print("Lat/lon of centroid", header['lat'])
    print("1 + n bits per voxel:", header['nbits'])


def get_voxels(header, levels, data):
    """Generate a set of xyz position in the bounding box of the VOLA data."""
    depth = header['depth']
    indexes = get_all_indexes(levels, depth)
    indexes, dataindexes = traverse_indexes(
        [], indexes, depth - 1, [0] * depth)

    voxels = []
    voxel_data = []
    for index in indexes:
        voxels.append(bu.xyz_from_sparse_index(index))

    if header['nbits'] > 0:
        # we could do this for each level but only care about the bottom
        for dindex in dataindexes:
            voxel_data.append(data[depth - 1][dindex[-1]])

    return voxels, voxel_data


def get_coords(header, voxels):
    """Get the CRS coordinate value of the voxels."""
    if header['crs'] == 2000:
        print("coordinate system was not set, returning voxel coordinates.")
        return voxels
    else:
        coordinates = []
        for vox in voxels:
            normed = [float(x) / (header['sidelength']) for x in vox]
            scaled = [x * max(header['diff']) for x in normed]

            coord = [x + y for x, y in zip(scaled, header['offset'])]
            coordinates.append(coord)
        return coordinates


def get_voxel(coord, header, levels):
    """Check if a voxel exists and return the block index value."""
    depth = header['depth']
    indexes = bu.sparse_indexes(coord, depth)
    blockindexes = []
    blockidx = 0

    for d in range(depth):
        block = levels[d][blockidx]
        bitval = bu.read_bit(block, indexes[d])

        if bitval == 0:
            return False
        else:
            blockindexes.append(blockidx)
            nextblockidx = -1
            maskstr = '1' * (indexes[d] + 1)
            mask = np.uint(int(maskstr, 2))
            block = block & mask
            block = np.uint64(block)
            nextblockidx += bu.count_bits(block)

            for b in range(blockidx):
                nextblockidx += bu.count_bits(levels[d][b])
            blockidx = nextblockidx
    return blockindexes


def save_file(filename, header, coords, data):
    """CHECK IF BOUNDING BOXES MATCH."""
    bbox = [[header['minx'], header['miny'], header['minz']],
            [header['maxx'], header['maxy'], header['maxz']]]

    volatree = VolaTree(header['depth'], bbox, header['crs'],
                        False, header['nbits'])
    volatree.cubify(coords, data)
    volatree.writebin(filename)


# def set_voxel(coord, header, levels, data, byteindexes, bytevals):
#     """Set the value of a voxel at a given position (Not implemented)."""
#     index = get_voxel(coord)
#     if not index:
#         print("can only set occupied voxels")
#     else:
#         dataval = data


def get_all_indexes(levels, depth):
    """Parse the levels and record the indexes which are set to one."""
    bitcnt = 1
    indexes = []

    for d in range(depth):
        newcnt = 0
        indexes.append([])
        for b in range(bitcnt):
            chunk_indexes = bu.get_indexes(levels[d][b])
            newcnt += len(chunk_indexes)
            indexes[d].append(chunk_indexes)
        bitcnt = newcnt
    return indexes


def traverse_indexes(prev, levels, depth, levelcnt):
    """
    Recursive function for depth first traversal of the level array.

    It is not a tree but nested arrays so our BFS position is recorded
    because the breadth position is required!
    """
    traversed = []
    dataindexes = []
    if depth > 0:
        block = levels[0][levelcnt[depth]]
        for index in block:
            lowerlist = prev + [index]
            result, dindex = traverse_indexes(lowerlist, levels[1:],
                                              depth - 1, levelcnt)

            traversed.extend(result)
            dataindexes.extend(dindex)
    else:
        block = levels[0][levelcnt[depth]]
        for index in block:
            dataindexes.append(levelcnt[::-1])
            traversed.append(prev + [index])
    levelcnt[depth] += 1
    return traversed, dataindexes


def get_chunk(filereader):
    """Utility function for reading 64 bit chunks."""
    data = filereader.read(8)
    if not data:
        print("prematurely hit end of file")
        exit()
    bit64chunk = struct.unpack('Q', data)[0]
    return bit64chunk


def get_binary_indexes(coordinates):
    """Generate binary coordinates."""
    bin_coordinates = []
    for coord in coordinates:
        coord = ("{:08b}".format(coord[0]),
                 "{:08b}".format(coord[1]),
                 "{:08b}".format(coord[2]),)
        bin_coordinates.append(coord)
    return bin_coordinates


def generate_map(coordinates, header, start_height):
    """For a given starting height, compress the maps to a plane."""
    imagedir = "./images/"
    basename = os.path.basename(header['filename']).replace('.vol', 'map.pgm')
    filename = imagedir + basename
    if not os.path.exists(imagedir):
        os.makedirs(imagedir)

    depth = header['depth']
    sidelen = pow(4, depth)
    level = np.zeros((sidelen, sidelen, sidelen))

    for coord in coordinates:
        level[coord] = 1

    # cut off lower levels
    level = level[:, :, start_height:]
    bitmap = np.sum(level, axis=2)
    # a cheeky switcheroo
    bitmap[bitmap > 0] = -1
    bitmap = bitmap + 1
    write_pgm(filename, bitmap)


def numpy_grid(coordinates, header):
    """For a given starting height, compress the maps to a plane."""
    datadir = "./dataset/"
    basename = os.path.basename(
        header['filename']).replace(
        '.vol',
        'heighttrain.npy')
    filename = datadir + basename
    if not os.path.exists(datadir):
        os.makedirs(datadir)

    depth = header['depth']
    sidelen = pow(4, depth)
    level = np.zeros((sidelen, sidelen, sidelen))
    sumlevel = np.zeros((sidelen, sidelen, sidelen))

    for coord in coordinates:
        sumlevel[coord] = 1

    bitmap = np.sum(sumlevel, axis=2)

    for coord in coordinates:
        # Randomly deleting voxels, bias for height
        # x, y, z = coord
        # zfactor = z / 10
        # if zfactor < 1:
        #     zfactor = 1
        #
        # likelihood = 0.0001 + ((0.1 * bitmap[x][y]) / zfactor)
        #
        # if random.random() > likelihood:
        level[coord] = 1
    np.save(filename, level)


def slice_layers(coordinates, header):
    """Slice the 3D model into image planes."""
    imagedir = "./images/"
    if not os.path.exists(imagedir):
        os.makedirs(imagedir)

    for depth in range(1, header['depth'] + 1):
        bitshift = 2 * (header['depth'] - depth)
        sidelen = pow(4, depth)
        level = np.zeros((sidelen, sidelen, sidelen))

        for coord in coordinates:
            coord = tuple([x >> bitshift for x in coord])
            level[coord] = 1

        for z in range(level.shape[2]):
            fname = imagedir + "depth{}-{:03d}.pgm".format(depth, z)
            write_pgm(fname, level[:, :, z])


def write_pgm(fname, data):
    """Output the data as ascii PGM images."""
    sidelen = data.shape[0]
    hdr = "P2\n" + str(sidelen) + " " + str(sidelen) + " 1\n"
    np.savetxt(fname, data, fmt='%i', delimiter=' ', header=hdr, comments='')


if __name__ == '__main__':
    main()
