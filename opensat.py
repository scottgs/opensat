import argparse
import datetime
import os
import requests
import sys
import gdal
import numpy as np
import scipy as sp
from tqdm import tqdm
from processing import *
from mask import *
import Landsat
import Sentinel


parser = argparse.ArgumentParser()
parser.add_argument("command", nargs='?', default='false', help="type of command")
parser.add_argument("-s", "--scene", help="satellite scene id")
parser.add_argument("-l", "--location", help="satellite scene path and row")
parser.add_argument("-b", "--bands", help="satellite bands")
parser.add_argument("-d", "--date", help="satellite date")
parser.add_argument("-c", "--clouds", help="prc of clouds")
parser.add_argument("-p", "--processing", help="prc of clouds")
parser.add_argument("-m", "--mask", help="prc of clouds")
parser.add_argument("-i", "--image", help="Image file name")
parser.add_argument("-t", "--transforms", help="transform(s) to perform. Transforms seperated by \',\'")
args = parser.parse_args()


class bcolors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

command = args.command.lower()   #type of command
scene = args.scene  #scene ID
image = args.image

tokens = args.transforms.split('/')
transforms = []
params = []
for i in range(0, len(tokens)):
    params.append([])
for i in range(0, len(tokens)):
    #print(str(i))
    transforms.append( tokens[i].split('[')[0] )
    tmp = (tokens[i].split('[')[1]).replace("]", "")
    print(str( len(params) ))
    params[i] = ( tmp.split(",") )
print(str(transforms))

location = args.location  #scene path
processing_bands = args.processing
mask = args.mask
search_matches = []  #list of bands IDs

def get_list(pic):  #get json from developmentseed API
    api_url = getattr(pic, 'api_url')
    print(api_url)
    r = requests.get(api_url)
    status = r.status_code
    if status == 200:
        return r.json()
    else:
        sys.exit(bcolors.FAIL + str(status) + " ERROR. Please check later." + bcolors.ENDC)


def create_directory(pic): #check if directory exists and craete if needed
    home = os.path.expanduser("~")
    pictures_directory = home + "/opensat/"
    if not os.path.exists(pictures_directory):
        os.mkdir(os.path.expanduser(pictures_directory))

    satellite_directory = pictures_directory + satellite
    if not os.path.exists(satellite_directory):
        os.mkdir(os.path.expanduser(satellite_directory))

    scene_directory = satellite_directory + "/" + getattr(pic, 'scene')
    if not os.path.exists(scene_directory):
        os.mkdir(os.path.expanduser(scene_directory))
    return scene_directory


def scene_links(pic): #create links for particular scene
    band_url = getattr(pic, 'band_url')
    all_bands = pic.get_all_bands()
    if args.bands == None:  #download all files
        urls = [band_url + band for band in all_bands]
    else:  #download seperate bands
        bands = args.bands.split(',')
        if satellite == "landsat":
            urls = [band_url + "_B" + band + ".TIF" for band in bands]
            urls.append(band_url + "_MTL.txt")
        else:
            bands = [band.zfill(2) if len(band) == 1 else band for band in bands]
            urls = [band_url + "B" + band + ".jp2" for band in bands]
            urls.append(band_url + "tileInfo.json")
    return urls


def download(pic):
    dowloaded_path = create_directory(pic)
    urls = scene_links(pic)
    for url in urls:
        local_filename = url.split('/')[-1]
        check = os.path.isfile(dowloaded_path + "/" + local_filename)
        if check == True:
            print(local_filename + " is already downloaded")
        else:
            for i in range(10):
                try:
                    response = requests.get(url, stream=True)
                    # response = requests.get(url, stream=True, timeout=240)
                    local_filename = url.split('/')[-1]
                    headers = response.headers
                    if "content-length" not in headers:
                        print(bcolors.FAIL + "Ooops... SERVER ERROR. Looks like " + local_filename + " doesn't exist" + bcolors.ENDC)
                    else:
                        print("Downloading " + local_filename)
                        file_chunk_size = int(int(headers['content-length'])/99)
                        with open(dowloaded_path + "/" + local_filename, 'wb') as f:
                            for chunk in tqdm(response.iter_content(chunk_size = file_chunk_size), unit='%'):
                                f.write(chunk)
                        print(bcolors.OKGREEN + "Success! " + local_filename + " is downloaded!" + bcolors.ENDC)
                        print("This file is saved to " + dowloaded_path + "\n")
                except requests.exceptions.Timeout:
                    continue
                break
    # is_processing()


def processing(bands):
    if satellite == "landsat" and "8" in bands:
        process = PanSharpen(scene, bands, satellite)
        process.run()
    else:
        if command == "search":
            for match in search_matches:
                process = Processing(match['id'], bands, satellite)
                process.run()
        elif command == "download":
            process = Processing(scene, bands, satellite)
            process.run()
    if mask != None:
        mask_img = Mask(process.output_file, mask)
        mask_img.run()



def bulk_objects(): # download multiple scenes
    for match in search_matches:
        if satellite == "landsat":
            scene_d = Landsat(match["id"], None)
        elif satellite == "sentinel":
            scene_d = Sentinel(match["id"],None)
        download(scene_d)
    if processing_bands != None:
        processing(processing_bands)


def download_yes_no(question): #bulk download prompt
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}

    sys.stdout.write(bcolors.WARNING + question + bcolors.ENDC)
    choice = raw_input().lower()
    if choice in valid:
        if valid[choice] == True:
            print("Downloading collection of scenes...")
            bulk_objects()
    else:
        sys.stdout.write(bcolors.FAIL + "Invalid answer. Please respond with 'yes' or 'no'.\n" + bcolors.ENDC)


def search_results(pic):  #print search results
    search = get_list(pic)
    print(bcolors.OKGREEN + "===== List of scenes: =====" + bcolors.ENDC + "\n")

    def print_match():
        search_matches.append({'id': scene["scene_id"], 'clouds': scene["cloud_coverage"]})
        print("scene id: " + bcolors.OKGREEN + scene["scene_id"] + bcolors.ENDC)
        print("date:", scene["date"])
        print("cloud coverage:", str(scene["cloud_coverage"]) + "%")
        print ("preview:", scene["thumbnail"] + "\n")

    def print_summary():
        match_cases = len(search_matches)
        min_cloud = min(search_match['clouds'] for search_match in search_matches)
        max_cloud = max(search_match['clouds'] for search_match in search_matches)
        print("\n======= SEARCH SUMMARY =======")
        if match_cases > 0:
            print(bcolors.OKGREEN + str(match_cases) + " scenes were found for the search area" + bcolors.ENDC)
            print(bcolors.OKGREEN + "The min cloud coverage is " + str(min_cloud) + "%" + bcolors.ENDC)
            print(bcolors.OKGREEN + "The max cloud coverage is "  +  str(max_cloud) + "%" + bcolors.ENDC)
            download_yes_no("Do you want to download all scenes? " + "[y/n]")
        else:
            print(bcolors.FAIL + "No results were found" + bcolors.ENDC)


    if (args.clouds != None) & (args.date != None): #check for cloud and date conditions
        clouds = float(args.clouds)
        date = args.date.split(",")
        date_start = datetime.datetime.strptime(date[0], "%Y-%m-%d")
        date_end = datetime.datetime.strptime(date[1], "%Y-%m-%d")
        for scene in search["results"]:
            data_scene = datetime.datetime.strptime(scene["date"], "%Y-%m-%d")
            if (data_scene < date_end) & (data_scene > date_start) & (scene["cloud_coverage"] <= clouds):
                print_match()
        print_summary()

    elif args.clouds != None: #check for clouds condition
        clouds = float(args.clouds)
        for scene in search["results"]:
            if scene["cloud_coverage"] <= clouds:
                print_match()
        print_summary()

    elif args.date != None: #check for date condition
        date = args.date.split(",")
        date_start = datetime.datetime.strptime(date[0], "%Y-%m-%d")
        date_end = datetime.datetime.strptime(date[1], "%Y-%m-%d")
        for scene in search["results"]:
            data_scene = datetime.datetime.strptime(scene["date"], "%Y-%m-%d")
            if (data_scene < date_end) & (data_scene > date_start):
                print_match()
        print_summary()

    else: # print all scenes
        for scene in search["results"]:
            print_match()
        print_summary()


def get_image_to_transform():
    home = os.path.expanduser("~")

    # Might be useful later, but not utilized currently
    if scene != None and scene[0] == "L":
        pathName = home + "/opensat/landsat/" + scene + "/opensat_info.json"
    elif scene != None and scene[0] == "S":
        pathName = home + "opensat/sentinel/" + scene + "/opensat_info.json"

    pathName = home + "/opensat/opensat_info.json"

    # Load existing JSON data file
    try:
        with open(pathName) as f:
            data = json.load(f)
    except json.decoder.JSONDecodeError:
        data = []

    # Check if the operation command specified exists already
    try:
        imageJSONIndex = data[image]
    except KeyError:
        imageJSONIndex = -1;

    tmp = image

    # If it does not exist, add it and perform the operation
    if imageJSONIndex == -1:
        data[image] = {"transform":{"name":"", "params":[]}, "variants":{}}
    else:
        # Save a reference the data list at the found index
        arr = data[image]["variants"]
        foundTransforms = []
        searchStr = image.split('.')[0] + "_" + transforms[0] + params[0][0] + "." + image.split('.')[1]
        # Run while the list of transforms is not empty
        while transforms != []:
            print("Attempting to find requested image and transform...")
            found = -1 # Flag for breaking the loop
            # Iterate through the child array and look for matching transform
            for i in range(0, len(arr)):
                try:
                    if arr[searchStr]["transform"]["name"] == transforms[0] and validate_transform_params(arr, searchStr) != -1:
                        print("Previously transformed image found! The image " + searchStr + " was transformed using " + transforms[0])
                        foundTransforms.append(transforms.pop(0)) # Remove the first transform
                        params.pop(0)
                        # Will return to tell what image to start transforming
                        tmp = searchStr

                        arr = arr[searchStr]["variants"]
                        found = 1
                        break
                except KeyError:
                    break
            # If not matching transform is found, break the loop
            if found == -1:
                #data[image]["variants"][searchStr] = {"transform":{"name":transforms[0], "params":params[0]}, "variants":{}}
                arr[searchStr] = {"transform":{"name":transforms[0], "params":params[0]}, "variants":{}}
                print(str(arr))
                break
            if transforms != []:
                searchStr = searchStr.split('.')[0] + "_" + transforms[0] + "." + searchStr.split('.')[1]

        print("The closest image the specified image and transform(s) is: " + str(tmp) + " which has had the " + str(foundTransforms) + " transforms performed.")
        if transforms != []:
            print("Run the " + str(transforms) + " transforms on the image " + str(tmp) + " to get the desired result.")

        # TODO: Once transforms are added, add a for loop to cycle through all
        # reamining members of 'transforms' and perform the specified transforms
        # in order

    # Save new data back to JSON
    with open(pathName, 'w') as outfile:
        json.dump(data, outfile, sort_keys = True, indent = 4, ensure_ascii = False)

    return tmp

def validate_transform_params(arr, searchStr):
    for i in range(0, len(arr[searchStr]["transform"]["params"])):
        #print("Comparing: " + str(arr[searchStr]["transform"]["params"][i]) + " and " + str(params[i]))
        if arr[searchStr]["transform"]["params"][i] != params[0][i]:
            return -1
    return 1;

if scene == None and location != None:
    if "," in location:
        satellite = "landsat"
        picture = Landsat(None, location)
    elif "," not in location:
        satellite = "sentinel"
        picture = Sentinel(None, location)


if command == "search":
    search_results(picture)


elif command == "download":
    if scene != None and scene[0] == "L": # Check satellite and type of command
        satellite = "landsat"
        picture = Landsat.Landsat(scene, None)
    if scene != None and scene[0] == "S":
        satellite = "sentinel"
        picture = Sentinel.Sentinel(scene, None)
    download(picture)
    if processing_bands != None:
        processing(processing_bands)

# TODO: Update for other operation commands
elif command == "transform" and image != "" and transforms != []:
    # Get the image that we should actually transforms
    # This will also alter the list of transforms/params needed to execute
    img = get_image_to_transform()

    #Open existing dataset
    src_img = gdal.Open(img)

    #Open output format driver, see gdal_translate --formats for list
    format = "GTiff"
    driver = gdal.GetDriverByName(format)

    # New filename for the transformed image
    dst_img = image.split('.')[0]
    for i in range(0, len(transforms)):
        dst_img = dst_img + "_" + transforms[i] + params[i][0]
    dst_img = dst_img + "." + image.split('.')[1]

    res = []

    print(str(transforms))
    #print(str(params))

    if transforms != []:
        for i in range(0, len(transforms)):
            np_arr = src_img.GetRasterBand(1).ReadAsArray()
            if transforms[i] == "rotate":
                res = sp.ndimage.rotate(np_arr, float(params[i][0]))
            elif transforms[i] == "denoise":
                res = sp.ndimage.gaussian_filter(np_arr, float(params[i][0]))
            elif transforms[i] == "erosion":
                res = sp.ndimage.grey_erosion(np_arr, structure=np.ones((int(params[i][0]),int(params[i][1])))).astype(np_arr.dtype)
            elif transforms[i] == "dilation":
                res = sp.ndimage.grey_dilation(np_arr, structure=np.ones((int(params[i][0]),int(params[i][1])))).astype(np_arr.dtype)
            elif transforms[i] == "open":
                res = sp.ndimage.grey_opening(np_arr, structure=np.ones((int(params[i][0]),int(params[i][1])))).astype(np_arr.dtype)
            elif transforms[i] == "close":
                res = sp.ndimage.grey_closing(np_arr, structure=np.ones((int(params[i][0]),int(params[i][1])))).astype(np_arr.dtype)
            elif transforms[i] == "tophat":
                res = sp.ndimage.white_tophat(np_arr, structure=np.ones((int(params[i][0]),int(params[i][1])))).astype(np_arr.dtype)
            elif transforms[i] == "sharpen":
                res = np_arr + float(params[i][0]) * (np_arr - np_arr)
            #elif transforms[i] == "scale":
            #elif transforms[i] == "translate":

    else:
        print("Image with the desired transforms already exists under filename:" + img)

    if res != []:
        sp.misc.imsave(dst_img, res)
    #driver.CreateCopy(dst_img, src_img, 0)
