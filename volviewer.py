"""
VOLA viewer.

VTK and python 3 based viewer for showing the voxel data for individual tiles.
Uses the VOLA reader to process the individual sparse vola tiles (.vol)
@author Jonathan Byrne
"""
from __future__ import print_function
import vtk
import volareader as vr
import struct


def main():
    """Draw the voxels for a given filename."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "fname", help="the name of the file you want to open", type=str)
    args = parser.parse_args()

    if not args.fname.endswith(".vol"):
        print("It needs to be an vol file!")
        exit()

    header, levels, data = vr.open_file(args.fname)
    coords, coord_data = vr.get_voxels(header, levels, data)
    colors = []

    if header['nbits'] > 0:
        for datum in coord_data:
            bytestr = struct.pack('<Q', datum)
            bytevals = [b for b in bytestr]
            colors.append([bytevals[0], bytevals[1], bytevals[2]])
    else:
        for coord in coords:
            colors.append([200, 200, 200])

    view_voxels(coords, colors)


def view_voxels(positions, colors):
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
    cube_source.SetXLength(1)
    cube_source.SetYLength(1)
    cube_source.SetZLength(1)
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
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    ren = vtk.vtkRenderer()
    ren.AddActor(actor)

    renwin = vtk.vtkRenderWindow()
    renwin.SetSize(1000, 1000)
    renwin.AddRenderer(ren)
    iren = vtk.vtkRenderWindowInteractor()
    iren.SetRenderWindow(renwin)
    renwin.Render()
    iren.Initialize()
    iren.Start()


if __name__ == "__main__":
    main()
