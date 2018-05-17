# Superclass for all opensat supported satellites

import argparse
import datetime
import os
import requests
import sys
from tqdm import tqdm
from processing import *
from mask import *

class Satellite:
    def __init__(self, scene, path):
        print("testing")
