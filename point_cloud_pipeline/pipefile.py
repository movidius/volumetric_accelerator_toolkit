import argparse
import subprocess
import xml.etree.ElementTree as ET
from os.path import dirname as getdirname, abspath as getabspath, isfile, split as separatefilename
from re import split
from time import sleep as delayexecution

# supply desired vola depth and the supported types, followed by their script file prefix
VOLA_DEPTH = 4
DENSE = False
NBITS = False
CRS = 2905
supported_types = {
    'laz': 'las',
    'las': 'las',
    'stl': 'stl',
    'binvox': 'binvox',
    'bin': 'kitti',
    'dem': 'dem',
    'pcd': 'pcd',
    'ply': 'ply',
    'txt': 'txt',
    'xyz': 'xyz'
}

# parse the incoming filename

parser = argparse.ArgumentParser()
parser.add_argument('file_name', type=str)

args = parser.parse_args()

# get file name from inotifywait
#origin_filename = split('\s', args.file_name)[-1]

# if '.xml' in origin_filename:
#     if isfile(origin_filename.replace('.xml', '.laz')):
#         origin_filename = origin_filename.replace('.xml', '.laz')
#     elif isfile(origin_filename.replace('.xml', '.las')):
#         origin_filename = origin_filename.replace('.xml', '.las')

origin_filename = separatefilename(args.file_name)[-1]

# get extension and filename
extension = split('\.', origin_filename)[-1]
filename = split('\.' + extension, origin_filename)[0]

# find file's dir and the base directory
file_dir = separatefilename(args.file_name)[0] # eg /vola/point_cloud_pipeline/
working_dir = getdirname(file_dir) + '/'  # eg /vola/
file_dir = file_dir + '/' # need to separate for working_dir to work

RUN = True

# figure out which command needs to be used, and execute it
if extension != '':

    commands = {
        # if laz, translate and move laz to backup
        #'laz': ['pdal translate -i ' + file + ' -o ' + filename + 'las'],
        # if vol, move to backup
        'vol': [('mv ' + file_dir + origin_filename + ' ' + working_dir + 'data/' +
                 origin_filename.replace('__split__', '').replace('__filt__', ''))]
    }.get(extension, list())

    pipelinejson = None
    # split the file into 500x500 chunks if possible, converting to 1.2 laz 
    # and reading correct CRS we separate the splitting and filtering of chunks
    # to gain advantage of cores - pipeline only uses one core per pipeline. 
    # Therefore splitting into chunks first and running subsequent pipelines 
    # on each via xargs is faster.
    if (extension == 'laz' or extension == 'las') and '__split__' not in filename:
        if isfile(file_dir + filename + '.xml'):
            tree = ET.fromstring(subprocess.check_output(['lasinfo', file_dir + origin_filename, '--xml']))
            origin = tree.find('header').find('minimum')
            origin_x = origin.find('x').text
            origin_y = origin.find('y').text

            tree = ET.parse(file_dir + filename + '.xml').getroot()
            doctails = tree.find('MapProjectionDefinition').text

            epsg = list(filter(None, split('AUTHORITY\["EPSG",(\d+)\]\]', doctails)))[-1]
            CRS = 'EPSG:' + epsg #'PROJCS["NAD_1983_HARN_Oregon_Statewide_Lambert_Feet_Intl",GEOGCS["GCS_North_American_1983_HARN",DATUM["D_North_American_1983_HARN",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Lambert_Conformal_Conic"],PARAMETER["False_Easting",1312335.958005249],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-120.5],PARAMETER["Standard_Parallel_1",43.0],PARAMETER["Standard_Parallel_2",45.5],PARAMETER["Latitude_Of_Origin",41.75],UNIT["Foot",0.3048],AUTHORITY["EPSG",2994]]'.replace('\"', '\'')

            pipelinejson = ('{'
                '"pipeline": ['
                "{"
                '"type": "readers.las",'
                '"spatialreference":  "' + CRS + '",'
                '"filename": "' + file_dir + origin_filename + '"'
                "}, {"             
                '"type": "filters.range",'
                '"limits": "Classification![7:7],Z[-10:1000]"'
                "}, {"
                '"type": "filters.splitter",'
                '"length": "500",'
                '"origin_x": "' + origin_x + '",'
                '"origin_y": "' + origin_y + '"'
                "}, {"
                '"type": "writers.las",'
                '"compression": "LASZIP",'
                '"minor_version": 2,'
                '"dataformat_id": 0,'
                '"filename": "' + file_dir + filename + '__split___#.laz"'
                "} "
                "] "
                "}")

            commands.append('mv ' + file_dir + filename + '.xml ' + working_dir + filename + '.xml')
        else:
            RUN = False
    elif (extension == 'laz' or extension == 'las') and '__filt__' not in filename:
        pipelinejson = ('{'
            '"pipeline": ['
            '"' + file_dir + origin_filename + '",'
            "{"
            '"type": "filters.outlier",'
            '"method": "statistical",'
            '"multiplier": 12,'
            '"mean_k": 8'
            "}, {"
            '"type": "writers.las",'
            '"compression": "LASZIP",'
            '"minor_version": 2,'
            '"dataformat_id": 0,'
            '"filename": "' + file_dir + filename + '__filt__.laz"'
            "} "
            "] "
            "}")
    elif '__split__' in filename and '__filt__' in filename and (extension == '.laz' or extension == '.las'):
        tree = ET.fromstring(subprocess.check_output(['lasinfo', file_dir + '/' + origin_filename, '--xml']))
        origin = tree.find('header').find('srs').find('wkt').text

        CRS = list(filter(None, split('AUTHORITY\["EPSG","(\d+)"\]\]', origin)))[-1]

    if pipelinejson is not None:
        # print(pipelinejson)

        jsonfile = open(filename + 'jp.json', 'w')
        jsonfile.write(pipelinejson)
        jsonfile.close()

        commands.append('pdal pipeline ' + filename + 'jp.json')
        commands.append('rm ' + filename + 'jp.json')
        #if '__split__' not in filename:
        #    commands = ['pdal split ' + file_dir + file + ' ' + file_dir + filename + '__split__.laz length 500 --origin_x ' + origin_x + ' --origin_y ' + origin_y + ' --writers.las.minor_version=2 --writers.las.compression="LASZIP"']

    if RUN:
        # if neither laz, las or vol for special treatment, use generic script
        if len(commands) == 0 and extension in list(supported_types.keys()):
            commands.append('python3 ' + working_dir + 'vola_api/' + supported_types[extension] + '2vola.py ' + file_dir + origin_filename + ' ' + str(VOLA_DEPTH) + ' --crs ' + str(CRS) + (' -n' if NBITS else '') + (' -d' if DENSE else ''))

        # if we found a suitable command for the filetype, execute each in list
        if len(commands) != 0:
            # move whatever file we used to backup after done, as long as not vola
            if extension != 'vol' and '__split__' not in filename:
                commands.append('mv ' + file_dir + origin_filename + ' ' + working_dir + 'converted_clouds/' + origin_filename)
            if extension != 'vol' and '__split__' in filename:
                commands.append('rm ' + file_dir + origin_filename)

            for command in commands:
                # if working with las and equivalent .laz already in backup, remove instead of moving
                #if command[0] + command[1] == 'mv' and isfile(working_dir + '/converted_clouds/' + filename + 'laz') and extension != 'vol':
                #    command = 'rm ' + file_dir + '/' + file

                print("Executing " + command)
                print(subprocess.check_output(split('\s', command)))
