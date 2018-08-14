# Volumetric Accelerator Toolkit
A toolkit for experimenting with the volumetric Accelerator format.It contains 
a set of parsers to convert from LAZ/LAS, PLY, KITTI, PCD, STL and ASCII 3d models to vola.
It also contains areader (volareader.py) that allows the structure to be queried and output as
images or voxel maps. There is also a viewer (volaviewer.py) that allows individual or 
multiple volumes to be viewed.

## Installation

Obtaining the required packages from apt or pip is the only installation necessary.
After that point, simply cloning the api will have completed the installation.

### Dependencies

There are some packages that must be installed to leverage all of the functionality included.

apt

```
sudo apt install python3.5 libatlas-base-dev
```

pip3:

```
sudo pip3 install liblas laspy numpy numpy-stl pyproj vtk sphinxcontrib-programoutput plyfile
```

## How to use

### Converting to .vol

There are a variety of formats from which you can convert into vola. Currently supported are:
```
binvox
dem
kitty
las
laz (if compiling liblas manually with laszip)
npy array
pcd
ply
stl
txt
xyz
```

To convert any of these formats, a generic command may be used:
```
python3.5 *2vola.py vola_depth
```

Where * replaces any supported format, e.g. las2vola.py
Additionally, there are several extra arguments:
```
--crs [code] (the epsg coordinate system of the input)
--nbits, -n (tell the parser to use 1+nbits per voxel to automatically 
	add provided info to vola format, e.g. colour information)
--dense, -d (to output a dense point cloud)
```

### Obtaining information from the .vol file

After converting, you should be left with a relatively small .vol file.
This may be examined in several different ways. volareader.py will output various information depending on the arguments given.
```
python3.5 volareader.py vola_file.vol
	--voxels, -v (outputs the voxel positions within the VOLA bounds)
	--coordinates, -c (outputs the coordinates of the voxels within given coordinate system)
	--get, -g [x] [y] [z] (checks if voxel exists at given location and returns value if it does.)
	--bincoords, -b (outputs binary coordinates of the voxels provided)
	--images, -i (outputs the image planes for each depth as .pgm files)
	--map, -m [height] (outputs flattened map for given height as .pgm)
	--numpy, -n (outputs the occupancy grid to a numpy array)
```

### Visualising results

Using the vtk module, we can visualise the vola file

```
python3.5 volaviewer.py vola_file.vol
```

The argument '-ply' may also be added to output the vola representation to a .ply.

To generate more detailed documentation per file please go to the doc folder and run:
make html
or
make pdflatex
