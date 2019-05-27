import os
from datetime import datetime
import json




class Metafile:
    def __init__(self):
        self.origFilename = ""
        self.dotFilename = ""
        self.creationTime = None#
        self.lastChangesTime = None
        self.pointsList = []
    def __init__(self, filename: str, points: list) -> None:
        self.origFilename = ""
        self.dotFilename = ""
        self.creationTime = None  #
        self.lastChangesTime = None
        self.origFilename = filename#strings are immutable
        self.pointsList = list(points)#but lists needs to be copied
        self.creationTime = datetime.now()

    def __init__(self, origFilename: str, dotFilename: str, points: list) -> None:
        self.origFilename = ""
        self.dotFilename = ""
        self.creationTime = None  #
        self.lastChangesTime = None
        self.origFilename = origFilename
        self.dotFilename = dotFilename
        self.pointsList = list(points)
        self.creationTime = datetime.now()

    def setPoints(self, points: list):
        self.pointsList = list(points)

    def setOutFilename(self, filename):
        self.dotFilename = filename

    def getDict(self):
        jsonData = {}
        jsonData["pathOfOriginalImage"] = self.origFilename
        jsonData["pathOfMarkedImage"] = self.dotFilename
        jsonData["CreationTime"] = self.creationTime.strftime('%d-%m-%Y %H:%M')
        if self.lastChangesTime is None:
            self.lastChangesTime = datetime.now()
        jsonData["lastChangesTime"] = self.lastChangesTime.strftime('%d-%m-%Y %H:%M')
        jsonData['points'] = []
        for coord in self.pointsList:
            jsonData['points'].append([coord.x, coord.y])

        return jsonData

    def toJSON(self):
        self.lastChangesTime = datetime.now()
        dirname = os.path.dirname(self.dotFilename)
        if not os.path.isdir(dirname):
            os.mkdir(os.path.join(dirname, '.meta'))
        jsonFilename = os.path.join(dirname, '.meta')
        jsonFilename = os.path.join(jsonFilename, self.dotFilename + '.meta')

        #check if packet meta file exists
        packet_path = os.path.join(os.path.dirname(self.dotFilename), 'Packet.meta')
        if not os.path.isfile(packet_path):
            createPacketMeta(os.path.dirname(self.dotFilename))


        jsonData = self.getDict()

        #write json to file
        with open(jsonFilename, "w") as file:
            json.dump(jsonData, file)

        #add to packet meta file
        packet_file = open(packet_path, 'r')
        packet = json.load(packet_file)
        packet_file.close()
        packet['count'] += 1

        item = {
            'originalFilename': self.origFilename,
            'markedFilename': self.dotFilename,
            'metaFilename': jsonFilename
        }

        packet['data'].append(item)

        with open(packet_path, 'w') as file:
            json.dump(packet, file)

    def newIimeChanged(self):
        self.lastChangesTime = datetime.now()

    def fromJSON(self, jsonFilename):
        isFileExist = os.path.isfile(jsonFilename)
        if not isFileExist:
            return "File doesn't exist"

        jsonData = {}
        with open(jsonFilename, 'r') as file:
            jsonData = json.load(file)

        self.origFilename = jsonData["pathOfOriginalImage"]
        self.dotFilename = jsonData["pathOfMarkedImage"]
        self.creationTime = datetime.strptime(jsonData["CreationTime"], '%d-%m-%Y %H:%M')
        self.lastChangesTime = datetime.strptime(jsonData["lastChangesTime"], '%d-%m-%Y %H:%M')
        self.pointsList = jsonData['points']


def getOpeningFilename(file_name):
    '''
    :param file_name: path to image
    :return: path to image if exists or None and object of Metafile class
    '''
    # check meta files
    dir_name = os.path.dirname(file_name)
    packet_name = os.path.join(dir_name, 'Packet.meta')

    if os.path.isfile(packet_name):
        with open(packet_name, 'r') as packet_file:
            metaDict = json.load(packet_file)
            for data in metaDict['data']:
              if file_name ==  data['markedFilename']:
                  with open(data['metaFilename'], 'r') as f:
                      local_meta = json.load(f)
                      #metafile = Metafile(data['originalFilename'], data['markedFilename'], local_meta['points'])
                      metafile = Metafile('', '', [])
                      metafile.fromJSON(data['metaFilename'])
                      return data['originalFilename'], metafile

    metafile = Metafile(file_name, '', [])
    return file_name, metafile

def createPacketMeta(file_path: str) -> None:
    jsonData = {}
    jsonData['count'] = 0
    jsonData['data'] = []

    with open(os.path.join(file_path, 'Packet.meta'), 'w') as file:
        json.dump(jsonData, file)
