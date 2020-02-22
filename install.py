import os, shutil
import sys
import subprocess
import requests
import json
import re
import tarfile
import zipfile
from string import Template
from tqdm import tqdm

# libclang_rt.builtins needs to be installed inside clang, but we don't know the version number
# intitially so we'll fill it in by template at runtime
clangVersion = "0.0.0"

def cleanup():
    print("Cleaning up temporary folder")
    shutil.rmtree("temp")
    exit()

def checkProjectIsInstalled(projectName, dir, projectObj) -> bool:    
    global clangVersion
    binDir = "."
    try:
        binDir = projectObj["bin"]
    except KeyError:
        try:
            template = Template(projectObj["template_bin"])
            binDir = template.substitute(clang_version=clangVersion)
        except KeyError:
            binDir = dir

    binaries = projectObj["binaries"]
    if(os.path.exists(os.getcwd() + "/" + dir) and os.path.exists(os.getcwd() + "/" + binDir)):
        foundBinaries = 0
        neededBinaries = projectObj["binaries"]
        if(len(neededBinaries) > 0):
            place = 0
            for entry in os.scandir(binDir):
                if(entry.name == neededBinaries[place]):
                    print("Found " + neededBinaries[place] + " at " + entry.path)
                    foundBinaries += 1
                    place += 1
                if(foundBinaries == len(neededBinaries)):
                    return True
            #endfor
            return False
        else:
            return True
    else:
        return False

def getByDownload(src):
    match = re.search('([a-zA-Z\-_0-9.]+(zip|tar.gz))$', src)
    filename = match.group(1)
    temp_outputPathToFile = "temp/" + filename
    filetype = match.group(2)

    print("Getting via HTTP: " + src)

    response = requests.get(src, stream=True)

    if(response.status_code == 200):
        with open(temp_outputPathToFile, "wb") as handle:
            for data in tqdm(response.iter_content(), ascii=True, unit_scale=True, total=int(response.headers.get('Content-Length'))):
                handle.write(data) 

        if(filetype == "zip"):
            return zipfile.ZipFile(temp_outputPathToFile, "r")
        elif(filetype == "tar.gz"):
            return tarfile.open(temp_outputPathToFile, "r:gz")

    else:
        print("Requested src returned status code: " + str(response.status_code))
        cleanup()

def getByGit(src, dir):
    if(os.path.exists("./" + dir)): # Pull
        print("Repo already exists in " + dir + " directory, performing a git pull instead of cloning new")
        oldDir = os.getcwd()
        os.chdir(dir)
        gitCmd = ["git", "pull"]
        subprocess.run(gitCmd)
        os.chdir(oldDir)
    else: # Clone
        print("Getting via git: " + src)
        gitCmd = ["git", "clone", src, dir]
        subprocess.run(gitCmd)
    return

def buildProject(projectName, projectDir, buildDir, buildCmd):
    print("Building " + projectName)
    #if(os.path.isdir(buildDir)):
        #shutil.rmtree(buildDir)
    print("Running cmake...")
    subprocess.run(buildCmd)
    oldDir = os.getcwd()
    os.makedirs(buildDir, exist_ok=True)
    os.chdir(buildDir)
    print("Running ninja")
    subprocess.run(["ninja"])
    os.chdir(oldDir)
    return

def installProject(projectName, projectObj):
    global clangVersion
    print("Installing " + projectName + "...")
    
    dir = "."
    try:
        dir = projectObj["dir"]
    # libclang_rt special case
    except KeyError: 
        template = Template(projectObj["templated_dir"])
        dir = template.substitute(clang_version=clangVersion)

    if(checkProjectIsInstalled(projectName, dir, projectObj) == False):
        src = projectObj["src"]

        if(projectObj["get"] == "dl"):
            file = getByDownload(src)
            os.makedirs(dir, exist_ok=True)
            file.extractall(dir)
            file.close()
        elif(projectObj["get"] == "git"):
            getByGit(src, dir)
            buildCmd = projectObj["buildcmd"]
            buildDir = ""
            try:
                buildDir = projectObj["build_dir"]
            except KeyError:
                buildDir = "."
            buildProject(projectName, dir, buildDir, buildCmd)
    else:
        print(projectName + " appears to already be installed! Great!")

    if(projectName == "llvm-project"):
        oldDir = os.getcwd()
        buildDir = projectObj["build_dir"]
        os.chdir(buildDir + "/lib/clang/")
        for entry in os.scandir():
            if(entry.is_dir()):
                match = re.search('^([0-9]+.[0-9]+.[0-9]+)', entry.name)
                if(match):
                    clangVersion = match.group(0)
                    print("Found Clang Version: "+ clangVersion)
        os.chdir(oldDir)

def main(args):
    toolsFile = open("./tools.json", "r")
    tools = json.load(toolsFile)
    toolsFile.close()

    print("Creating temporary folder")
    os.makedirs("temp", exist_ok=True)

    print("Installing required components:")
    
    for requiredProject in tools["projects"]["required"]:
        installProject(requiredProject, tools["projects"]["required"][requiredProject])
    #for optionalProject in tools["projects"]["optional"]:
        #installProject(optionalProject, tools["projects"]["optional"][optionalProject])

    cleanup()


if __name__ == "__main__":
    main(sys.argv)
