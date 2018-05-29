import json
import subprocess
import xml.etree.ElementTree as ET
from os.path import isfile, split as separatefilename
from re import split

class CRSParser():
    # set initial attribute values
    def __init__(self, working_dir, limit, limit_string=''):
        self.LIM = limit_string
        self.working_dir = working_dir
        self.limit = limit
        self.CRS = 2000
        self.origin_x = '0'
        self.origin_y = '0'

    # parse the file/relevant file for CRS values and origin
    def parse(self, filename, current_dir):
        ext = filename.split('.')[-1]

        # get the origin if laz or las file
        if ext == 'laz' or ext == 'las':
            xml_tree = self.parseOrigin(filename, self.limit)

        # get crs from json file, laz/las or xml
        if isfile(current_dir + 'info.json'):
            jsonf = open(current_dir + 'info.json', 'r')
            infojson = json.load(jsonf)
            jsonf.close()

            self.CRS = infojson['crs']
        elif ext == 'laz' or ext == 'las':
            self.parseLASZ(xml_tree)
        elif isfile(filename.split('.')[0] + '.xml'):
            self.parseXML(filename, self.working_dir)
        else:
            raise Exception("No supported method of finding CRS")

    # parse the laz/las xml for the CRS info
    def parseLASZ(self, tree):
        origin = tree.find('header').find('srs').find('wkt').text

        if origin is not None:
            CRS_attempt = list(filter(None, split(r'AUTHORITY\["EPSG","(\d+)"\]*', origin)))[-1]

            try:
                CRS_attempt = int(CRS_attempt)
            except:
                CRS_attempt = None
                pass

        if CRS_attempt is not None:
            self.CRS = CRS_attempt

    # parse the adjacent XMl file for CRS
    def parseXML(self, filename, working_dir):
        xml_filename = filename.split('.')[0] + '.xml'
        tree = ET.parse(xml_filename).getroot()
        doctails = tree.find('MapProjectionDefinition').text

        epsg = list(filter(None, split(r'AUTHORITY\["EPSG",(\d+)\]*', doctails)))[-1]

        try:
            CRS_attempt = int(epsg)
        except:
            CRS_attempt = None
            pass

        if CRS_attempt is not None:
            self.CRS = CRS_attempt

        # move xml file to converted
        dest_filename = working_dir + 'converted_clouds/' + separatefilename(xml_filename)[-1]
        self.checkOutput('mv ' + xml_filename + ' ' + dest_filename)

    # parse origin from laz/las file
    def parseOrigin(self, filename, limit=False):
        if filename is not None:
            tree = ET.fromstring(self.checkOutput('lasinfo ' + filename + ' --xml',
                ret=True, limit=limit))
        else:
            raise Exception('No origin source provided in LAS/LAZ')

        origin = tree.find('header').find('minimum')
        self.origin_x = origin.find('x').text
        self.origin_y = origin.find('y').text

        return tree

    # uses subprocess to run the command specified, possibly returning the output
    def checkOutput(self, command, ret=False, limit=True):
        if command[0:2] == 'rm' or command[0:2] == 'mv':
            limit = False

        if not ret:
            print(subprocess.check_output(((self.LIM if limit else '') + command).split(' ')))
        else:
            return subprocess.check_output(((self.LIM if limit else '') + command).split(' '))
