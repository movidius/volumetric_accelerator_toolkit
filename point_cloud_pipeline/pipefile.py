import argparse
import subprocess
import xml.etree.ElementTree as ET
from os.path import dirname as getdirname, abspath as getabspath, isfile, split as separatefilename
from re import split
from time import sleep as delayexecution, localtime, strftime

# supply desired vola depth and the supported types, followed by their script file prefix
VOLA_DEPTH = 4
DENSE = False
NBITS = False
CRS =  3089 #2000
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
limtime = int(strftime('%H%M', localtime()))
CPU_LIMIT = 50 if (limtime > 730 and limtime < 1830) else 100
LIM = 'cpulimit -l ' + str(CPU_LIMIT) + ' -z '

# parse the incoming filename

parser = argparse.ArgumentParser()
parser.add_argument('file_name', type=str)

args = parser.parse_args()

origin_filename = separatefilename(args.file_name)[-1]

# get extension and filename
extension = split('\.', origin_filename)[-1]
filename = split('\.' + extension, origin_filename)[0]

SPLIT = '__split__' in filename
FILTERED = '__filt__' in filename

# find file's dir and the base directory
file_dir = separatefilename(args.file_name)[0] # eg /vola/point_cloud_pipeline/
working_dir = getdirname(file_dir) + '/'  # eg /vola/
file_dir = file_dir + '/' # need to separate for working_dir to work

RUN = True

def checkOutput(command, ret=False, limit=True):
    if not ret:
        print(subprocess.check_output(split('\s', (LIM if limit else '') + command)))
    else:
        return subprocess.check_output(split('\s', (LIM if limit else '') + command))

# figure out which command needs to be used, and execute it
if extension != '':

    commands = {
        # if vol, move to backup
        'vol': [('mv ' + file_dir + origin_filename + ' ' + working_dir + 'data/' +
                 origin_filename.replace('__split__', '').replace('__filt__', ''))]
    }.get(extension, list())

    pipelinejson = None

    if extension == 'laz' or extension == 'las':
        CRS_attempt = None

        if not SPLIT or FILTERED:
            # need to get the current CRS to tell the vola api
            tree = ET.fromstring(checkOutput('lasinfo ' + file_dir + origin_filename + ' --xml', ret=True))
            origin = tree.find('header').find('srs').find('wkt').text

            if origin is not None:
                CRS_attempt = list(filter(None, split('AUTHORITY\["EPSG","(\d+)"\]\]', origin)))[-1]

                print("Found CRS in file: " + CRS_attempt)

                origin = tree.find('header').find('minimum')
                origin_x = origin.find('x').text
                origin_y = origin.find('y').text

        if not SPLIT and CRS_attempt is None:
            if isfile(file_dir + filename + '.xml'):
                tree = ET.fromstring(checkOutput('lasinfo ' + file_dir + origin_filename + ' --xml', ret=True))
                origin = tree.find('header').find('minimum')
                origin_x = origin.find('x').text
                origin_y = origin.find('y').text

                tree = ET.parse(file_dir + filename + '.xml').getroot()
                doctails = tree.find('MapProjectionDefinition').text

                epsg = list(filter(None, split('AUTHORITY\["EPSG",(\d+)\]\]', doctails)))[-1]
                CRS_attempt = epsg

                commands.append('mv ' + file_dir + filename + '.xml ' + working_dir + 'converted_clouds/' + filename + '.xml')

            else: # if no CRS and no xml, don't run
                RUN = False

        if CRS_attempt is not None and isinstance(CRS_attempt, int):
            CRS = CRS_attempt

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
            #if '__split__' not in filename:
            #    commands = ['pdal split ' + file_dir + file + ' ' + file_dir + filename + '__split__.laz length 500 --origin_x ' + origin_x + ' --origin_y ' + origin_y + ' --writers.las.minor_version=2 --writers.las.compression="LASZIP"']

    if RUN:
        # if neither laz, las or vol for special treatment, use generic script
        if len(commands) == 0 and extension in list(supported_types.keys()):
            commands.append('python3 ' + working_dir + 'vola_api/' + supported_types[extension] + '2vola.py ' + file_dir + origin_filename + ' ' + str(VOLA_DEPTH) + ' --crs ' + str(CRS) + (' -n' if NBITS else '') + (' -d' if DENSE else ''))

        # if we found a suitable command for the filetype, execute each in list
        if len(commands) != 0:
            # move whatever file we used to backup after done, as long as not vola
            if extension != 'vol' and not SPLIT:
                commands.append('mv ' + file_dir + origin_filename + ' ' + working_dir + 'converted_clouds/' + origin_filename)
            if extension != 'vol' and SPLIT:
                commands.append('rm ' + file_dir + origin_filename)

            for command in commands:
                # if working with las and equivalent .laz already in backup, remove instead of moving
                #if command[0] + command[1] == 'mv' and isfile(working_dir + '/converted_clouds/' + filename + 'laz') and extension != 'vol':
                #    command = 'rm ' + file_dir + '/' + file

                print(strftime('%d/%m %H:%M:%S', localtime()) + " - Executing " + command)
                checkOutput(command)
