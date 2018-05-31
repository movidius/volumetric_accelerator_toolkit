"""
VOLA viewer.

VTK and python 3 based viewer for showing the voxel data for either single or
multiple tiles. Uses the VOLA reader and the .vola format for multiple tiles
@author Jonathan Byrne & Anton Shmatov
@copyright 2018 Intel Ltd (see LICENSE file).
"""
from __future__ import print_function
import json
import struct
import vtk
import volareader as vr


def main():
    """Draw the voxels for a given filename or dataset."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "fname", help="the name of the file you want to open", type=str)
    parser.add_argument("--ply", help="output a ply file", action='store_true')
    args = parser.parse_args()
    # set up the renderer to add the points to
    renderer = vtk.vtkRenderer()
    if args.ply:
        polyappend = vtk.vtkAppendPolyData()
        print("generating output file for the mesh: out.ply")
    else:
        polyappend = None

    if args.fname.endswith(".vola"):
        read_vola(args.fname, renderer, polyappend)
    elif args.fname.endswith(".vol"):
        read_vol(args.fname, renderer, polyappend)
    else:
        print("It needs to be a vol file or a vola json file!")
        exit()

    # now render everything
    print("finished reading files.")
    if polyappend is not None:
        plyWriter = vtk.vtkPLYWriter()
        plyWriter.SetFileName("out.ply")
        plyWriter.SetInputConnection(polyappend.GetOutputPort())
        plyWriter.Write()
    renwin = vtk.vtkRenderWindow()
    renwin.SetSize(1000, 1000)
    renwin.AddRenderer(renderer)
    iren = vtk.vtkRenderWindowInteractor()
    iren.SetRenderWindow(renwin)
    renwin.Render()
    iren.Initialize()
    iren.Start()


def read_vola(filename, renderer, polyappend):
    """# read the contents of all files listed in the .vola json file."""
    with open(filename) as vola_file:
        vola_data = json.load(vola_file)

    for vola in vola_data['files']:
        header, levels, data = vr.open_file(vola['filename'])
        voxels, voxel_data = vr.get_voxels(header, levels, data)
        coords = vr.get_coords(header, voxels)
        colors = []
        if header['nbits'] > 0:
            for datum in voxel_data:
                bytestr = struct.pack('<Q', datum)
                bytevals = [b for b in bytestr]
                colors.append([bytevals[0], bytevals[1], bytevals[2]])
        else:
            for _ in coords:
                colors.append([200, 200, 200])
        add_voxels(coords, colors, renderer, polyappend, header['cubesize'])


def read_vol(filename, renderer, polyappend):
    """Read individual vola file."""
    header, levels, data = vr.open_file(filename)
    coords, coord_data = vr.get_voxels(header, levels, data)
    colors = []

    if header['nbits'] > 0:
        for datum in coord_data:
            bytestr = struct.pack('<Q', datum)
            bytevals = [b for b in bytestr]
            colors.append([bytevals[0], bytevals[1], bytevals[2]])
    else:
        for _ in coords:
            colors.append([200, 200, 200])
    add_voxels(coords, colors, renderer, polyappend, 1)


def add_voxels(positions, colors, renderer, polyappend, cubesize=1):
    """
    VTK based viewer for sparse VOLA files (.vol).

    Maps VOLA and draws opengl cubes for voxels and their color information.
    """
    # Point array for holding voxel positions
    points = vtk.vtkPoints()
    for pos in positions:
        points.InsertNextPoint(*pos)
    polydata = vtk.vtkPolyData()
    polydata.SetPoints(points)

    # List for holding the color information
    color_def = vtk.vtkUnsignedCharArray()
    color_def.SetNumberOfComponents(3)
    color_def.SetNumberOfTuples(polydata.GetNumberOfPoints())
    for idx, color in enumerate(colors):
        color_def.InsertTuple3(idx, *colors[idx])
    polydata.GetPointData().SetScalars(color_def)

    # Use a cube glyph to quickly render the data
    cube_source = vtk.vtkCubeSource()
    cube_source.SetXLength(cubesize)
    cube_source.SetYLength(cubesize)
    cube_source.SetZLength(cubesize)
    cube_source.Update()

    glyph = vtk.vtkGlyph3D()
    # silly vtk change
    if vtk.VTK_MAJOR_VERSION < 6:
        glyph.SetInput(polydata)
    else:
        glyph.SetInputData(polydata)

    glyph.SetSourceConnection(cube_source.GetOutputPort())
    glyph.SetColorModeToColorByScalar()
    glyph.SetVectorModeToUseNormal()
    glyph.ScalingOff()

    # VTK Model: Mapper -> Actor -> Render
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(glyph.GetOutputPort())
    if polyappend is not None:
        polyappend.AddInputConnection(glyph.GetOutputPort())
        polyappend.Update()
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    renderer.AddActor(actor)


if __name__ == "__main__":
    main()
