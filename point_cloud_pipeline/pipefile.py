import argparse
import subprocess
import xml.etree.ElementTree as ET
from os import makedirs
from os.path import (dirname as getdirname, abspath as getabspath,
    isfile, split as separatefilename, isdir)
from re import split
from time import sleep as delayexecution, localtime, strftime
from crsparser import CRSParser

# supply desired vola depth and the supported types, followed by their script file prefix
VOLA_DEPTH = 3
DENSE = False
NBITS = True
SIDE_LENGTH = 100
LIMIT = False

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

# limit cpu based on time of day
ltime = localtime()

if ltime.tm_wday not in {5, 6}: # do not limit on weekends
    limtime = int(strftime('%H%M', ltime))
    CPU_LIMIT = 25 if ((limtime >= 730 and limtime <= 1205) or 
        (limtime >= 1230 and limtime <= 1830)) else 100
    LIM = '' if CPU_LIMIT == 100 else 'cpulimit -l ' + str(CPU_LIMIT) + ' -z '
else:
    LIM = ''

# parse the incoming filename
parser = argparse.ArgumentParser()
parser.add_argument('file_name', type=str, help="File to consider processing.")

args = parser.parse_args()

origin_filename = separatefilename(args.file_name)[-1]

# get extension and filename
extension = split(r'\.', origin_filename)[-1]
filename = split(r'\.' + extension, origin_filename)[0]

SPLIT = '__split__' in filename
FILTERED = '__filt__' in filename

# find file's dir and the base directory
file_dir = separatefilename(args.file_name)[0] # eg /vola/point_cloud_pipeline/
working_dir = getdirname(file_dir) + '/'  # eg /vola/
file_dir = file_dir + '/' # need to separate for working_dir to work

if not isdir(working_dir + 'data/'):
    makedirs(working_dir + 'data/')

def fixVolName(filename):
    if filename[0] == '_':
        return filename[1:].replace('__split__', '').replace('__filt__', '')
    else:
        return filename.replace('__split__', '').replace('__filt__', '')

# parse the CRS and origin values from relevant file
crsparser = CRSParser(working_dir, LIMIT, LIM)
crsparser.parse(args.file_name, file_dir)
CRS = crsparser.CRS
origin_x = crsparser.origin_x
origin_y = crsparser.origin_y

# get useful function
checkOutput = crsparser.checkOutput

# figure out which command needs to be used, and execute it
if extension != '':

    commands = {
        # if vol, move to backup
        'vol': [('mv ' + file_dir + origin_filename + ' ' + working_dir + 'data/' +
                 fixVolName(origin_filename))]
    }.get(extension, list())

    pipelinejson = None

    if extension == 'laz' or extension == 'las':
        # split the file into 500x500 chunks if possible, converting to 1.2 laz 
        # and reading correct CRS we separate the splitting and filtering of chunks
        # to gain advantage of cores - pipeline only uses one core per pipeline. 
        # Therefore splitting into chunks first and running subsequent pipelines 
        # on each via xargs is faster.
        if not SPLIT:
            pipelinejson = ('{'
                    '"pipeline": ['
                    "{"
                    '"type": "readers.las",'
                    '"spatialreference":  "EPSG:' + str(CRS) + '",'
                    '"filename": "' + file_dir + origin_filename + '"'
                    "},")

            if CRS == 3089:
                pipelinejson = pipelinejson + ('{'
                    '"type": "filters.reprojection",'
                    '"in_srs": "EPSG:3089",'
                    '"out_srs": "EPSG:3088"'
                    '},')

            pipelinejson = pipelinejson + ('{'             
                '"type": "filters.splitter",'
                '"length": "' + str(SIDE_LENGTH) + '",'
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

        # filter the data
        if SPLIT and not FILTERED:
            pipelinejson = ('{'
                '"pipeline": ['
                '"' + file_dir + origin_filename + '",'
                "{"
                '"type": "filters.outlier",'
                '"method": "statistical",'
                '"multiplier": 12,'
                '"mean_k": 8'
                "}, {"
                '"type": "filters.range",'
                '"limits": "Classification![7:7],Z[-10:1000]"'
                "}, {"
                '"type": "writers.las",'
                '"compression": "LASZIP",'
                '"minor_version": 2,'
                '"dataformat_id": 0,'
                '"filename": "' + file_dir + filename + '__filt__.laz"'
                "} "
                "] "
                "}")
        
        if pipelinejson is not None:
            # print(pipelinejson)

            jsonfile = open(filename + 'jp.json', 'w')
            jsonfile.write(pipelinejson)
            jsonfile.close()

            commands.insert(0, 'pdal pipeline ' + filename + 'jp.json')
            commands.append('rm ' + filename + 'jp.json')

    # if neither laz, las or vol for special treatment, use generic script
    if len(commands) == 0 and extension in list(supported_types.keys()):
        commands.append('python3 ' + working_dir + 'vola_api/' + supported_types[extension] +
            '2vola.py ' + file_dir + origin_filename + ' ' + str(VOLA_DEPTH) +
            ' --crs ' + str(CRS) + (' -n' if NBITS else '') + (' -d' if DENSE else ''))

    # if we found a suitable command for the filetype, execute each in list
    if len(commands) != 0:
        # move whatever file we used to backup after done, as long as not vola
        if extension != 'vol' and not SPLIT:
            commands.append('mv ' + file_dir + origin_filename + ' ' + working_dir +
                'converted_clouds/' + origin_filename)
        if extension != 'vol' and SPLIT:
            commands.append('rm ' + file_dir + origin_filename)

        for command in commands:
            print(strftime('%d/%m %H:%M:%S', localtime()) + " - Executing " + command)
            checkOutput(command, limit=LIMIT)
