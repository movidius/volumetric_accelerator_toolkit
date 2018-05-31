# Point Cloud Processing Pipeline
Point Cloud Processing, made easier. 
This pipeline detects any new files that have been moved/written within
a specific directory, calling on a python script for each such new file.
The point cloud is first read using a resolved/specified CRS, then split into
100m x 100m chunks, starting at the minimum corner. The resulting point cloud
is then filtered to remove any outliers, thereafter being converted to vol using
the toolkit.
The default amount of processors that the pipeline uses, and hence number of
simultaneous files it considers is currently 6. This can be changed in _pipeline.sh_.

## Dependencies
Apart from the toolkit dependencies, only one package needs to be
installed onto your linux distribution - this is for keeping track of
new files in the folder.

```
sudo apt-get install inotify-tools
```

Additionally, if you wish to make use of the cpu limitation feature:

```
sudo apt-get install cpulimit
```

## Set-Up
By default, the script _pipeline.sh_ searches in the directory

```
/home/$USER/Documents/vola/drop/
```

So these directories should ideally exist.
Alternatively, the "DROPPATH" variable within _pipeline.sh_ should
be altered, providing a different directory.

## Usage
With the drop(or similar) directory created, simply running _pipeline.sh_
as a bash script will begin the pipeline. From here on out, any supported
point-cloud or 3D files that are _dropped_ into the specified folder will be
considered by the python script _pipefile.py_.

```
./pipeline.sh
```

Relevant changes that could be made to this file are the constant variables
near the top of the file, denoted in all caps.

```
VOLA_DEPTH = 3
DENSE = False
NBITS = True
SIDE_LENGTH = 100
LIMIT = True
```

Most of these parameters are self explanitory. Finding a point cloud's CRS comes
in order of local _info.json_ file within folder, CRS data from within the point
cloud file (only laz/las), or else a local and similarly named xml file (i.e. if
file is _qt1.laz_ then _qt1.xml_). When using the xml file variant, it is important
to copy all xml files before their point cloud variants, as the pipeline will
not backtrack on xml files that it did not find.
Hence, this CRS Override is used in most cases as data providers rarely
inject the CRS into every single file they provide. This override is only
used in the initial phase of splitting up, from thereon the CRS should be
contained within each file.

### CPU Limiting
The _LIMIT_ parameter is used to control the cpu limitation on a per-file
basis. If set to True, the cpu usage will be limited to 25% per process
during working hours, otherwise unlimited.

Any changes made to pipefile.py do not require a restart of the pipeline,
as they will take effect for the next file considered, unless you wish the
changes to be immediate on a running process - then everything must be restarted.

## Current Issues
- Unable to automatically detect CRS in some cases, issues with original las(z) files - use _info.json_
- Cannot backtrack to point cloud files whose xml was not found
- Issue with memory usage when dealing with large point clouds (>200 MB) (tested on 16 GB RAM & 12 GB SWP)
	- machine runs out of memory and has to kill a process to keep functioning
	- this can take effect when reading 2+ files. only relevant in splitting stage.
- CPU Limitation sometimes does not take effect - problem with cpulimit
- Occasionally lasinfo/pdal cannot read the las(z) files - corruption?
