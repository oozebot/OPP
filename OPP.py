#!/usr/bin/env python3
#Author: oozeBot, LLC
#Date: 8/19/2022
#Version: 0.1beta
#Purpose: Post-Processor for Slic3r variants
#================================================

#Commandline Arguments (Set default values here and input adjustments through Slic3r)
meshGrid = 0        #  Parameter: mesh=0/1/2
                    #  Mode 0 does not create a custom mesh grid
                    #  Mode 1 creates a custom mesh grid utilzing points
                    #       - Example: An object where X=100 and Y=200 with 5 points will probe the X-axis every 20mm per row
                    #                   and probe the Y-axis every 40mm per column, generating a 25 point mesh grid
                    #  Mode 2 creates a custom mesh grid utilizing spacing
                    #       - Example: An object where X=100 and Y=200 with 20mm spacing will probe the X-axis 5 times per row
                    #                  and probe the Y-axis 10 times per column, generating a 50 point mesh grid
                    #  Requires the following code to be added to Printer Settings > Custom G-code > Start G-code
                    #       ;FirstLayerMinMax: X{first_layer_print_min[0]}:{first_layer_print_max[0]} Y{first_layer_print_min[1]}:{first_layer_print_max[1]}
meshPoints = 5      #  Parameter: points=5
                    #  Used in conjunction with mesh mode 1
                    #  Defaults to 5 points for both the X & Y axis
meshSpacing = 15    #  Parameter: spacing=XX
                    #  Used in conjueciton wi th mesh mode 2
                    #  Defaults to a 15x15 grid for the X & Y axis
startCode = "M9000" #  Parameter: start=XXXXXX | start=M9000 | start=begin.g
                    #  Requires defined file in the system folder
xOffset = 19        #  Parameter: xOffset=XX | xOffset=19
                    #  Used to send center coordinates of mesh as a parameter of startCode
yOffset = 19        #  Parameter: yOffset=XX | yOffset=19
                    #  Used to send center coordinates of mesh as a parameter of startCode
minGrid = 10        #  Parameter: minGrid=10 | minGrid=19
                    #  Used to set minimum safe coordinate the build plate can be probed
maxGrid = 300       #  Parameter: maxGrid=10 | maxGrid=300
                    #  Used to set the maximum safe coordinate the build plate can be probed

#================================================
import sys
import time
from tempfile import mkstemp
from shutil import move, copymode
from os import sep, fdopen, remove
from tracemalloc import start

#================================================
header = ";=== OPP HEADER ==="
minMax = ";FirstLayerMinMax:"
gridCreated = False
meshError = False
newLine = "\n"

#================================================
def roundDown(num, spacing):
  num = float(num)
  num = int(num) + 1
  x = num % spacing
  return num - x

#================================================
def roundUp(num, spacing):
  num = float(num)
  num = int(num) + 1
  x = num % spacing
  x = spacing - x
  return num + x

#================================================
def getDimensions(pattern):
  x = -1
  returnVal = ""
  for line in lines:
    x = x + 1
    if line[:len(pattern)] == pattern:
      returnVal = line[len(pattern):].upper()
      break
  return returnVal

#================================================
def createMesh1Grid(value):
  global meshError
  if value[:1] == "X" or value[:1] == "Y":
    axis = value[:1]
    value = value[1:].replace('"', '')
    min,max = value.split(":")
    min = float(min)-1
    max = float(max)+1
    min = int(min)
    max = int(max)
    if (min) < minGrid or max > maxGrid:
      print(" -- ERROR: grid will not fit in the defined area! No mesh will be created.")
      input(" -- Press Enter to Acknowledge:")
      time.sleep(2)
      meshError = True
      return ""
    else:
      return axis + str(min) + ":" + str(max)

#================================================
def createMesh2Grid(value, spacing):
  global meshError
  if value[:1] == "X" or value[:1] == "Y":
    axis = value[:1]
    value = value[1:].replace('"', '')
    min,max = value.split(":")
    min = roundDown(min, spacing)
    max = roundUp(max, spacing)
    if (min) < minGrid or max > maxGrid:
      print(" -- ERROR: grid will not fit in the defined area! No mesh will be created.")
      input(" -- Press Enter to Acknowledge:")
      meshError = True
      return ""
    else:
      return axis + str(min) + ":" + str(max)

#================================================
def calcGrid(value, spacing):
  if value[:1] == "X" or value[:1] == "Y":
    value = value[1:].replace('"', '')
    min,max = value.split(":")
    min = roundDown(min, spacing)
    max = roundUp(max, spacing)
    return (max - min) / spacing

#================================================
def findMesh1Center(value, xOffset, yOffset):
  if value[:1] == "X" or value[:1] == "Y":
    axis = value[:1]
    value = value[1:].replace('"', '')
    min,max = value.split(":")
    min = float(min)-1
    min = int(min)
    max = float(max)+1
    max = int(max)
    if axis == "X":
      return axis + str(((max - min) / 2) + min - xOffset)
    if axis == "Y":
      return axis + str(((max - min) / 2) + min - yOffset)

#================================================
def findMesh2Center(value, spacing, xOffset, yOffset):
  if value[:1] == "X" or value[:1] == "Y":
    axis = value[:1]
    value = value[1:].replace('"', '')
    min,max = value.split(":")
    min = roundDown(min, spacing)
    max = roundUp(max, spacing)
    if axis == "X":
      return axis + str(((max - min) / 2) + min - xOffset)
    if axis == "Y":
      return axis + str(((max - min) / 2) + min - yOffset)

#================================================
def updateArray(pattern, newvalue, instances):
  x = -1
  cnt = 0
  for line in lines:
    x = x + 1
    if cnt == instances: break
    if line[:len(pattern)] == pattern:
      lines[x] = newvalue
      cnt = cnt + 1

#================================================
def isNum(val):
  try:
    float(val)
    return True
  except ValueError:
    return False

#================================================
if __name__ == "__main__":
  print("oozeBot Post-Processor")
  time.sleep(.25)

  for arg in sys.argv[1:]:
    if arg[:5].upper() == "MESH=":
      temp = arg[5:]
      if isNum(temp):
        meshGrid = int(temp)
    elif arg[:6].upper() == "START=":
      startCode = arg[6:].strip()
    elif arg[:7].upper() == "POINTS=":
      temp = arg[7:]
      if isNum(temp):
        meshPoints = int(temp)
    elif arg[:8].upper() == "SPACING=":
      temp = arg[8:]
      if isNum(temp):
        meshSpacing = float(temp)
    elif arg[:8].upper() == "XOFFSET=":
      temp = arg[8:]
      if isNum(temp):
        xOffset = float(temp)
    elif arg[:8].upper() == "YOFFSET=":
      temp = arg[8:]
      if isNum(temp):
        yOffset = float(temp)
    elif arg[:8].upper() == "MINGRID=":
      temp = arg[8:]
      if isNum(temp):
        minGrid = float(temp)
    elif arg[:8].upper() == "MAXGRID=":
      temp = arg[8:]
      if isNum(temp):
        maxGrid = float(temp)

  sourceFile = sys.argv[len(sys.argv)-1]
  sourceFile = sourceFile.replace(sep,'/')

  #== Read source file ================
  file = open(sourceFile, 'r')
  lines = file.readlines()
  file.close()

  print(" -- file loaded into memory")
  time.sleep(.25)

  headerData = newLine +    ";== Modified by OPP: oozeBot Post Processor" + newLine
  headerData = headerData + ";== Source: https://github.com/oozeBot/OPP" + newLine + newLine
  generatedGrid = False

  if meshGrid > 0:
    dims = getDimensions(minMax)
    if len(dims) > 0:
      M557 = dims.strip()
      M557 = M557.split(" ")
      if isinstance(M557, list):
        if len(M557) >= 2:
          if meshGrid == 1: #Points
            meshData = ";== " + str(int(meshPoints * meshPoints)) + " point mesh grid" + newLine
            meshData = meshData + "M557 " + createMesh1Grid(M557[0]) + " " + createMesh1Grid(M557[1]) + " P" + str(meshPoints) + newLine 
            meshData = meshData + startCode + " C\"mesh\" " + findMesh1Center(M557[0], xOffset, yOffset) + " " + findMesh1Center(M557[1], xOffset, yOffset) + newLine
            if not meshError:
              headerData = headerData + meshData
              gridCreated = True
          elif meshGrid == 2: #Spacing
            meshData = ";== " + str(int(calcGrid(M557[0], meshSpacing) * calcGrid(M557[1], meshSpacing))) + " point mesh grid" + newLine
            meshData = meshData + "M557 " + createMesh2Grid(M557[0], meshSpacing) + " " + createMesh2Grid(M557[1], meshSpacing) + " S" + str(meshSpacing) + newLine
            meshData = meshData + startCode + " C\"mesh\" " + findMesh2Center(M557[0], meshSpacing, xOffset, yOffset) + " " + findMesh2Center(M557[1], meshSpacing, xOffset, yOffset) + newLine
            if not meshError:
              headerData = headerData + meshData
              gridCreated = True
  if not gridCreated:
    headerData = headerData + ";== Initialization script" + newLine
    headerData = headerData + startCode + newLine
  
  updateArray(minMax, "", 1)
  updateArray(header, headerData + newLine, 1)

  print(" -- processing complete")
  time.sleep(.25)

  #== Write source file ===============
  ofile = open(sourceFile, 'w')
  for line in lines:
    ofile.write(line)
  ofile.close()

  print(" -- file saved to disk")
  time.sleep(.25)
  print("done!")
  time.sleep(1)