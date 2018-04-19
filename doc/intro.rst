Introduction
============
Volumetric Accelerator (VOLA) is a compact data structure that unifies computer vision
and 3D rendering and allows for the rapid calculation of connected
components, per-voxel census/accounting, CNN inference, path planning
and obstacle avoidance. Using a  hierarchical bit array format allows
it to run efficiently on embedded systems and maximize the level of data
compression. The proposed format allows massive scale volumetric data to
be used in embedded applications where it would be inconceivable to
utilize point-clouds due to memory constraints. Furthermore, geographical
and qualitative data is embedded in the file structure to allow it to be
used in place of standard point cloud formats.

`A paper detailing the format and its applications can be downloaded here <http://jonathan-byrne.com/vola_applications.pdf>`_

This toolkit is developed to allow for comparison and analysis with existing
formats. An overview of the toolkit functions and their interactions are shown
in the image below:

.. figure:: apioverview.png
   :align: center

   layout of the VOLA toolkit 1.0


The parsers (xxx2vola) will convert to the VOLA format, embedding information
where information is available. The reader and the viewer will allow you to
examine the data in VOLA format.

There is sample data for each of the formats in the samplefiles folder

An example workflow for a LIDAR file containing color information is as follows:

./las2vola samplefiles/cchurchdecimated 3 -n

this will parse the las file to a vola depth of 3 and the -n flag means the
color information will be automatically added to VOLA file

./volareader samplefiles/cchurchdecimated.vol -c

print the coordinates of the voxels

./volaviewer samplefiles/cchurchdecimated.vol

view the vola file.
