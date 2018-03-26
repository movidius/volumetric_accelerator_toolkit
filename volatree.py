"""
The VOLA tree for generating sparse VOLA files.

@author Jonathan Byrne & Anton Shmatov
"""
from __future__ import print_function
import pyproj
import numpy as np
import binutils as bu


class VolaTree(object):
    """VOLA tree representation."""

    def __init__(self, max_depth, bbox, crs, dense, nbits):
        """Create levels, set bounding box, etc."""
        self.version = 1
        self.headersize = 80
        self.max_depth = max_depth
        self.bbox = bbox
        self.crs = crs
        self.sparse = not dense
        self.nbits = nbits
        self.difference = [i - j for i, j in zip(self.bbox[1], self.bbox[0])]
        self.sidedivisions = pow(4, max_depth)
        self.levels = []
        # assign vol arrays for each level. L5 slow at 1073741824 subdivisions
        # and side length of 1024
        for i in range(max_depth):
            if self.nbits > 0:
                level = [np.uint64(0)] * (pow(64, i) * 2)
                self.levels.append(level)
            else:
                level = [np.uint64(0)] * (pow(64, i))
                self.levels.append(level)

    def cubify(self, points, pointsdata=None):
        """Split the point cloud into integer voxel coordinates."""
        uniquecubes = {}
        maxlen = max(self.difference)
        bmin = np.array(self.bbox[0])

        norms = bu.normalize_np(points, bmin, bmin + maxlen)
        keys = np.int_(np.around((self.sidedivisions - 1) * norms))

        # use idx to not conflict with inbuilt id()
        for idx, key in enumerate(map(tuple, keys)):
            if isinstance(pointsdata, np.ndarray):
                uniquecubes[key] = pointsdata[idx]
            else:
                uniquecubes[key] = [255, 255, 255, 255, 255, 255, 255]

        print("Computed number of occupied voxels:", len(uniquecubes))
        print("Now building vola tree")
        for key in sorted(uniquecubes.keys()):
            self.setvoxel(key, uniquecubes[key])

    def setvoxel(self, coords, vals):
        """Set bit to 1 for different levels."""
        x, y, z = coords[0], coords[1], coords[2]
        payload = 0
        if self.nbits > 0:
            for offset, elem in enumerate(vals):
                if elem > 255:
                    raise ValueError("byte payload must be less than 255")
                payload += int(elem) << (offset * 8)
            payload = np.uint64(payload)

        if self.sparse:
            self.set_sparse(x, y, z, payload)
        else:
            for i in range(len(self.levels)):
                self.setlevel(i, (x, y, z), payload)

    def set_sparse(self, x, y, z, nbits):
        """Sparse structure for vola tree."""
        indexes = bu.sparse_indexes((x, y, z), self.max_depth)

        for i, idx in enumerate(indexes):
            # Level 0: all values mapped to one vol
            if i == 0:
                self.levels[i][0] = bu.set_bit(self.levels[i][0], idx)
                if nbits > 0:
                    self.levels[i][1] = nbits
            else:
                # Level N: all values mapped to offset vol
                prev = indexes[:i]
                off = 0
                for lev, elem in enumerate(reversed(prev)):
                    off += elem * (pow(64, lev))

                self.levels[i][off] = bu.set_bit(self.levels[i][off], idx)
                if nbits > 0:
                    nbitsoffset = pow(64, (i)) + off
                    self.levels[i][nbitsoffset] = nbits

    def wgs84_position(self):
        """The lat/ lon coordinates of the centroid of the volume."""
        centroid = [(i + j) / 2 for i, j in zip(self.bbox[1], self.bbox[0])]
        localcrs = pyproj.Proj(init='epsg:' + str(self.crs))
        wgs84 = pyproj.Proj(init='epsg:4326')
        transform = pyproj.transform(localcrs, wgs84, centroid[0], centroid[1])
        lat = np.float64(transform[1])
        lon = np.float64(transform[0])
        print("Lat:", lat, "lon:", lon)
        return lat, lon

    def setlevel(self, i, coord, twobits):
        """
        Setting occupancy bit and secondary data (twobits) on a given level.

        It implements the dense tree and uses a global linear mapping.
        """
        sidelength = pow(4, (i + 1))
        divisor = pow(4, self.max_depth - (i + 1))
        x = coord[0] // divisor
        y = coord[1] // divisor
        z = coord[2] // divisor
        index = x + (y * sidelength) + (z * pow(sidelength, 2))
        offset = index // 64
        bit = index % 64
        self.levels[i][offset] = bu.set_bit(self.levels[i][offset], bit)
        if twobits:
            twobitsoffset = pow(64, (i)) + offset
            self.levels[i][twobitsoffset] = twobits

    def countlevels(self):
        """Measure all the pixels in the tree."""
        for idx, level in enumerate(self.levels):
            empty = 0
            used = 0
            occupied = 0
            unoccupied = 0

            elements = np.array(level) # count all used cubes
            nz = np.count_nonzero(elements)
            used += nz
            empty += elements.size - nz

            # count all occupied bits - define set of uint8s to work with numpy
            dt = np.dtype((np.uint64, {'0':(np.uint8, 0), '1':(np.uint8, 1),
                '2':(np.uint8, 2), '3':(np.uint8, 3), '4':(np.uint8, 4),
                '5':(np.uint8, 5), '6':(np.uint8, 6), '7':(np.uint8, 7)}))
            bn = elements.view(dtype = dt)

            # concat uint8s for easiness
            total_bin = np.concatenate([bn['0'], bn['1'], bn['2'], bn['3'],
                bn['4'], bn['5'], bn['6'], bn['7']])

            # unpack and count bits
            level_occupied = np.count_nonzero(np.unpackbits(total_bin))
            occupied += level_occupied
            unoccupied += 64 * nz - level_occupied

            print("level", idx, "empty", empty, "used", used, "occupied",
                  occupied, "unoccupied", unoccupied)

    def writebin(self, filename):
        """Output binary levels, Header information."""
        print("writing file:", filename)
        outfile = open(filename, 'wb')

        headersize = np.uint32(self.headersize)  # bytesize
        version = np.uint16(self.version)

        if self.sparse:
            mode = 0
        else:
            mode = 1

        mode = np.uint8(mode)
        depth = np.uint8(self.max_depth)
        nbits = np.uint32(self.nbits)
        epsgcode = np.uint32(self.crs)
        lat, lon = self.wgs84_position()

        # writing out header
        outfile.write(headersize)
        outfile.write(version)
        outfile.write(mode)
        outfile.write(depth)
        outfile.write(nbits)
        outfile.write(epsgcode)
        outfile.write(lat)
        outfile.write(lon)
        for elem in self.bbox:
            outfile.write(np.float64(elem))

        # then write all the points
        for lval, level in enumerate(self.levels):
            volcount = 0
            for vol in level:
                if self.sparse:
                    if vol != 0:
                        volcount += 1
                        outfile.write(vol)
                else:
                    volcount += 1
                    outfile.write(vol)

            print("level:", lval, "output:", volcount)
        outfile.close()
