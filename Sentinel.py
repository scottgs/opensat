# Subclass for ESA Sentinel class satellite

from Satellite import Satellite

class Sentinel(Satellite):
    'Generates attributes for Sentinel images'

    def __init__(self, scene, path):
      if scene != None:
        self.scene = scene
        self.utm_code = scene[18:20]
        self.lat_band = scene[20]
        self.square = scene[21:23]
        self.year = scene[9:13]
        self.month = scene[13:15]
        self.day =  scene[15:17]
        self.sequence = scene[-1]
        if self.month[0] == "0": #check for zeroes
            self.month = self.month[1]
        if self.day[0] == "0":
            self.day = self.day[1]
        self.band_url = "http://sentinel-s2-l1c.s3.amazonaws.com/tiles/" + self.utm_code + "/" + self.lat_band + "/" + self.square + "/" + self.year + "/" + self.month + "/" + self.day + "/" + self.sequence + "/"

      elif scene == None:
        self.utm_code = path[0:2]
        self.lat_band = path[2]
        self.square = path[3:5]
        self.api_url = "https://api.developmentseed.org/satellites?search=satellite_name:sentinel-2+AND+((grid_square:" + self.square + "+AND+latitude_band:" + self.lat_band + "+AND+utm_zone:" + self.utm_code + "))&limit=2000"

    def get_all_bands(self):
        return ["B01.jp2", "B02.jp2", "B03.jp2", "B04.jp2", "B05.jp2", "B06.jp2", "B07.jp2", "B08.jp2", "B09.jp2", "B10.jp2", "B11.jp2", "B12.jp2", "tileInfo.json"]
