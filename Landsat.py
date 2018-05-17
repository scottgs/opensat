# Subclass for NASA Landsat class satellite

from Satellite import Satellite

class Landsat(Satellite):
    'Generates attributes for Landsat images'

    def __init__(self, scene, path):
      if scene != None:
        self.scene = scene
        self.path = scene[3:6]
        self.row = scene[6:9]
        self.band_url = "http://landsat-pds.s3.amazonaws.com/L8/" + self.path + "/" + self.row + "/" + self.scene + "/" + self.scene

      elif scene == None:
        path = path.split(',')
        self.path = path[0]
        self.row = path[1]
        self.api_url = "https://api.developmentseed.org/satellites?search=satellite_name:landsat-8+AND+((path:" + self.path + "+AND+row:" + self.row + "))&limit=2000"

    def get_all_bands(self):
        return ["_B1.TIF", "_B2.TIF", "_B3.TIF", "_B4.TIF", "_B5.TIF", "_B6.TIF", "_B7.TIF", "_B8.TIF", "_B9.TIF", "_B10.TIF", "_B11.TIF", "_BQA.TIF", "_MTL.txt"]
