import sys
import shutil
import os
import os.path
import wget
import json
import zipfile
from urllib.request import urlopen
from urllib.error import HTTPError
from datetime import datetime, timedelta
import subprocess as sp  # Allows Windows 10 commands to be executed

# Debug level 0 is no debug messages, 1 is error debug messages only, 2 is brief debug
# messages only and 3 is full debug messages
DEBUG_LEVEL = 3

PATH_SEPARATOR = "/"
TEMP_DIR = "Temp"
DOWNLOADS_DIR = TEMP_DIR + PATH_SEPARATOR + "Downloads"
UNZIPPED_DIR = TEMP_DIR + PATH_SEPARATOR + "Unzipped"
LIB_DIR = TEMP_DIR + PATH_SEPARATOR + "lib"

CIRCUITPYTHON_VERSION = "6.x"

JSON_FILE_URL_TEMPLATE = "https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases/download/{0}/adafruit-circuitpython-bundle-{0}.json"
BUNDLEFLY_JSON_FILE_PATH = DOWNLOADS_DIR + PATH_SEPARATOR + "adafruit-circuitpython-bundle.json"
MAX_LOOK_BACK_DAYS = 365

REQUIRED_LIBS_FILE = "required_libs.txt"

DEL_CMD = "del"
DEL_CMD_PARAMS = "/f /q /s {0}:\\lib\\*.*"
RMDIR_CMD = "rmdir"
RMDIR_CMD_PARAMS = "/q /s {0}:\\lib"
MKDIR_CMD = "mkdir"
MKDIR_CMD_PARAMS = "{0}:\\lib"
MKDIR_PACKAGE_CMD_PARAMS = "{0}:\\lib\\{1}"
COPY_CMD = "copy"
COPY_MODULE_CMD_PARAMS = '"{0}\\{1}.{2}" {3}:\\lib'
XCOPY_CMD = "xcopy"
XCOPY_PACKAGE_CMD_PARAMS = '"{0}\\{1}" "{2}:\\lib\\{1}" /e /q'

MODULE_EXT = "mpy"

LIBRARY_URL_TEMPLATE = "{0}/releases/download/{1}/{2}-{3}-mpy-{1}.zip"
LIBRARY_ARCHIVE_FILE_TEMPLATE = "{0}/{1}-{2}-mpy-{3}.zip"
LIBRARY_DIR_PATH_TEMPLATE = "{0}/{1}-{2}-mpy-{3}"


# From URL https://stackoverflow.com/questions/4188326
def get_drive_letters():
    args = ["wmic",
            "logicaldisk",
            "get",
            "caption,description,providername",
            "/format:csv"]

    process = sp.run(args, check=True, shell=True, stdout=sp.PIPE, universal_newlines=True)
    results = []
    for line in process.stdout.split("\n"):
        if line:
            line_split = line.split(",")
            if len(line_split) == 4 and line_split[1][1] == ":":
                results.append(line_split[1][0])
    return results


def count_files_and_dirs(path):
    total_files = 0
    total_folders = 0
    for root, folders, files in os.walk(path):
        total_files += len(files)
        total_folders += len(folders)
    return total_files, total_folders


def bar_custom(current, total, width=80):
    if DEBUG_LEVEL > 2:
        indicators = "=" * int((current / total) * 73)
        spaces = " " * (73 - len(indicators))
        percent = int((current / total) * 100)
        sys.stdout.write("\r" + "{0:>3}% [{1}{2}]".format(percent, indicators, spaces))
        sys.stdout.flush()


def url_exists(url):
    try:
        urlopen(url)
        return True
    except HTTPError:
        if DEBUG_LEVEL == 1 or DEBUG_LEVEL > 2:
            print(url + " does not exist")
        return False


def main(args=None):
    if args is None or len(args) < 2 or len(args[1]) != 1 or not args[1].isalpha():
        if DEBUG_LEVEL > 0:
            print("No target drive letter (as single alpha character) provided")
            print("Aborting!")
        return

    drive = args[1].upper()

    if drive not in get_drive_letters():
        if DEBUG_LEVEL > 0:
            print("Target drive <{0}:> is not mounted".format(drive))
            print("Aborting!")
        return

    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    shutil.rmtree(LIB_DIR, ignore_errors=True)
    os.mkdir(TEMP_DIR)
    os.mkdir(LIB_DIR)
    os.mkdir(DOWNLOADS_DIR)
    os.mkdir(UNZIPPED_DIR)

    # The name of the text file that contains the list of all the required CircuitPython
    # library entries that need updating - Note: this could be enhanced to allow a command
    # line input of the REQUIRED_LIBS_FILE at run-time
    if not os.path.isfile(REQUIRED_LIBS_FILE):
        if DEBUG_LEVEL > 0:
            print("Cannot find file <{0}>".format(REQUIRED_LIBS_FILE))
            print("Aborting!")
        return

    with open(REQUIRED_LIBS_FILE, "r") as required:
        requirements = []
        for requirement in required:
            requirement = requirement.replace("\n", "").strip()
            if len(requirement) > 0 and not requirement[0] == "#":
                requirements.append(requirement.split("|"))

    custom_libs_directory = requirements[0][0]

    if not os.path.isdir(custom_libs_directory):
        if DEBUG_LEVEL > 0:
            print("Custom libraries directory <{0}> not found".format(custom_libs_directory))
            print("Aborting!")
        return

    requirements = requirements[1:]
    print("CircuitPython libraries update started - this may take some time")
    if DEBUG_LEVEL > 1:
        print("Target drive is mounted as <{0}:>".format(drive))
        print("\nSetting up <lib> directory on drive <{0}:>".format(drive))

    # Remove lib directory from target's file system
    if os.path.isdir("{0}:\\lib".format(drive)):
        if DEBUG_LEVEL > 2:
            print("Removing <lib> directory from drive <{0}:> - please wait...".format(drive))
        sp.run("{0} {1}".format(DEL_CMD, DEL_CMD_PARAMS.format(drive)), check=True, shell=True, stdout=sp.PIPE)
        sp.run("{0} {1}".format(RMDIR_CMD, RMDIR_CMD_PARAMS.format(drive)), check=True, shell=True, stdout=sp.PIPE)
        if DEBUG_LEVEL > 2:
            print("Removed  <lib> directory from drive <{0}:>".format(drive))
    else:
        if DEBUG_LEVEL > 0:
            print("\nNo <lib> directory found on drive <{0}:> so no need to remove!".format(drive))

    # Create lib directory on target's file system
    if DEBUG_LEVEL > 2:
        print("Creating <lib> directory on drive <{0}:> - please wait...".format(drive))
    sp.run("{0} {1}".format(MKDIR_CMD, MKDIR_CMD_PARAMS.format(drive)), check=True, shell=True, stdout=sp.PIPE)
    if DEBUG_LEVEL > 2:
        print("Created  <lib> directory on drive <{0}:>".format(drive))

    if DEBUG_LEVEL > 1:
        print("Completed set up of <lib> directory on drive <{0}:>".format(drive))

    # Process the requirements as specified in REQUIRED_LIBS_FILE - copy required custom library
    # modules and packages from <custom_libs_directory> into target drive's <lib> directory and
    # add required Adafruit library names to target list
    if DEBUG_LEVEL > 1:
        print("\nProcessing requirements file <{0}> - please wait...".format(REQUIRED_LIBS_FILE))
    if DEBUG_LEVEL > 2:
        print("Custom libraries path is <{0}>".format(custom_libs_directory))
        print("CircuitPython library requirements are:")
        for requirement in requirements:
            print("\t{0}".format(requirement))

    target_library_names = []
    for requirement in requirements:
        if len(requirement) < 2:
            if DEBUG_LEVEL > 0:
                print("Ignored [{0}] - this is not a valid requirement".format(requirement[0]))
            continue

        req_type = requirement[0]
        req_name = requirement[1]

        if req_type.upper() == "CP":
            if req_name == "":
                if DEBUG_LEVEL > 0:
                    print("Ignored a blank package name")
                continue

            if not os.path.isdir("{0}\\{1}".format(custom_libs_directory, req_name)):
                if DEBUG_LEVEL > 0:
                    print("Ignored [{0}] - this is not a custom library package".format(req_name))
                continue

            sp.run("{0} {1}".format(MKDIR_CMD, MKDIR_PACKAGE_CMD_PARAMS.format(drive, req_name)),
                   check=True, shell=True, stdout=sp.PIPE)
            sp.run("{0} {1}".format(XCOPY_CMD, XCOPY_PACKAGE_CMD_PARAMS.format(custom_libs_directory, req_name,
                                                                               drive)),
                   check=True, shell=True, stdout=sp.PIPE)

            if DEBUG_LEVEL > 2:
                strng = "Copied custom library package [{0}] to <lib> directory on drive <{1}:>"
                print(strng.format(req_name, drive))
        elif req_type.upper() == "CM":
            if req_name == "":
                if DEBUG_LEVEL > 0:
                    print("Ignored a blank module name")
                continue

            if not os.path.isfile("{0}\\{1}.{2}".format(custom_libs_directory, req_name, MODULE_EXT)):
                if DEBUG_LEVEL > 0:
                    print("Ignored [{0}] - this is not a custom library module".format(req_name))
                continue

            sp.run("{0} {1}".format(COPY_CMD,
                                    COPY_MODULE_CMD_PARAMS.format(custom_libs_directory, req_name, MODULE_EXT, drive)),
                   check=True, shell=True, stdout=sp.PIPE)
            if DEBUG_LEVEL > 2:
                strng = "Copied custom library module [{0}] to <lib> directory on drive <{1}:>"
                print(strng.format(req_name, drive))
        else:
            if req_type == "":
                if DEBUG_LEVEL > 0:
                    print("Ignored a blank requirement type")
            elif req_type == "AL":
                target_library_names.append(req_name)
                if DEBUG_LEVEL > 2:
                    print("Added Adafruit library [{0}] to target list".format(req_name))
            else:
                if DEBUG_LEVEL > 0:
                    print("Ignored [{0}, {1}] - this is not a valid requirement type".format(req_type, req_name))

    if DEBUG_LEVEL > 1:
        print("Processed requirements file <{0}>".format(REQUIRED_LIBS_FILE))
        print("\nGet latest Adafruit BundleFly JSON file - please wait...")

    if os.path.exists(BUNDLEFLY_JSON_FILE_PATH):
        os.remove(BUNDLEFLY_JSON_FILE_PATH)

    found = False
    days_to_look_back = 0
    check_datetime = now = datetime.now()

    while not found and days_to_look_back < MAX_LOOK_BACK_DAYS:
        check_datetime = now - timedelta(days=days_to_look_back)
        url = JSON_FILE_URL_TEMPLATE.format(check_datetime.strftime("%Y%m%d"))

        if url_exists(url=url):
            if DEBUG_LEVEL > 2:
                print("Downloading {0}".format(url))
            try:
                wget.download(url=url, out=BUNDLEFLY_JSON_FILE_PATH, bar=bar_custom)
                found = True
            except HTTPError as ex:
                if DEBUG_LEVEL > 0:
                    print("\n{0}".format(ex))
                else:
                    pass
        else:
            days_to_look_back += 1

    if not os.path.exists(BUNDLEFLY_JSON_FILE_PATH):
        if DEBUG_LEVEL > 0:
            print("\nAborting! BundleFly JSON file missing: {0}".format(BUNDLEFLY_JSON_FILE_PATH))
        return

    if DEBUG_LEVEL > 2:
        print()

    if DEBUG_LEVEL > 1:
        print("Got latest BundleFly JSON file dated {0}".format(check_datetime.strftime("%d-%m-%Y")))

    if DEBUG_LEVEL > 1:
        print("\nBuilding required Adafruit libraries list - please wait...")
    bundlefly_data = None
    with open(BUNDLEFLY_JSON_FILE_PATH, "r") as f:
        bundlefly_data = json.load(f)

    all_library_names = []
    for library_name in target_library_names:
        all_library_names.append(library_name)
        library_info = bundlefly_data[library_name]
        dependencies = library_info["dependencies"]

        def process_dependencies(deps):
            if len(deps) == 0:
                return

            if deps[0] not in all_library_names:
                all_library_names.append(deps[0])

            process_dependency(deps[0])

            process_dependencies(deps[1:])

        def process_dependency(dep):
            deps = bundlefly_data[dep]["dependencies"]

            if len(deps) == 0:
                if dep not in all_library_names:
                    all_library_names.append(dep)
                return

            process_dependencies(deps)

        process_dependencies(dependencies)

    if DEBUG_LEVEL > 1:
        print("Built required Adafruit libraries list")
    if DEBUG_LEVEL > 2:
        for library_name in all_library_names:
            print("\t{0}".format(library_name))
    if DEBUG_LEVEL > 1:
        print()
        print("Download required Adafruit libraries - please wait...")

    failed_libraries = []
    for library_name in all_library_names:
        if DEBUG_LEVEL > 2:
            print("Download Adafruit library {0}".format(library_name))
        library_info = bundlefly_data[library_name]
        version = library_info["version"]
        repo = library_info["repo"]
        pypi_name = library_info["pypi_name"]

        library_url = LIBRARY_URL_TEMPLATE.format(repo, version, pypi_name, CIRCUITPYTHON_VERSION)
        library_file_path = LIBRARY_ARCHIVE_FILE_TEMPLATE.format(DOWNLOADS_DIR, pypi_name, CIRCUITPYTHON_VERSION,
                                                                 version)

        if os.path.exists(library_file_path):
            os.remove(library_file_path)

        if DEBUG_LEVEL > 2:
            print("Downloading {0}".format(library_url))
        try:
            wget.download(url=library_url, out=library_file_path, bar=bar_custom)
        except HTTPError as ex:
            print("\tIgnored! Download failed due to {}\n".format(ex))
            failed_libraries.append((library_name, library_url, str(ex)))
            continue

        if not os.path.exists(library_file_path):
            if DEBUG_LEVEL > 0:
                print("\tIgnored! Archive file missing: {0}\n".format(library_file_path))
            failed_libraries.append((library_name, library_file_path, "Archive file missing"))
            continue

        with zipfile.ZipFile(library_file_path, "r") as zip_archive:
            zip_archive.extractall(UNZIPPED_DIR)

        os.chdir(LIBRARY_DIR_PATH_TEMPLATE.format(UNZIPPED_DIR, pypi_name, CIRCUITPYTHON_VERSION, version))
        shutil.copytree("lib", "../../../{0}".format(LIB_DIR), dirs_exist_ok=True)
        os.chdir("../../..")
        if DEBUG_LEVEL > 2:
            print("\nDownloaded Adafruit library {0}".format(library_name))

    if DEBUG_LEVEL > 1:
        print("Downloaded required Adafruit libraries")
    
    if DEBUG_LEVEL > 0:
        print("\nErrors processing required Adafruit libraries:-")
        print("--------")
        if failed_libraries == []:
            print("None")
        else:
            for failed_library in failed_libraries:
                print("Library {0} is not in <lib> directory on drive <{1}:>".format(failed_library[0], drive))
                print("Reason: {0}".format(failed_library[2]))
                print("Detail: {0}".format(failed_library[1]))

    if DEBUG_LEVEL > 1:
        print("\nCopying required Adafruit libraries to <lib> directory on drive <{0}:> - please wait...".format(drive))
    shutil.copytree(LIB_DIR, "{0}:/lib".format(drive), dirs_exist_ok=True)
    actual_files_count, actual_dirs_count = count_files_and_dirs("{0}:/lib".format(drive))
    if DEBUG_LEVEL > 1:
        strng = "Copied {0} file{1} {2} director{3} to <lib> directory on drive <{4}:>"
        print(strng.format(actual_files_count, "" if actual_files_count == 1 else "s",
                           actual_dirs_count, "y" if actual_dirs_count == 1 else "ies",
                           drive))
        print("Completed copying required Adafruit libraries to <lib> directory on drive <{0}:>".format(drive))

    shutil.rmtree(TEMP_DIR, ignore_errors=True)

    if DEBUG_LEVEL > 0:
        print()

    print("CircuitPython libraries update completed")


if __name__ == '__main__':
    main(args=sys.argv)
