#------------ A RESEARCHERS TOOL FOR INTERPRETTING REAL TIME WATER LEVEL-----------#

# # --- AUTHOR: Sambhavi Joshi --- # #

####################################################################

#PLEASE SET YOUR WORKING SPACE BY PUTTING THE ADDRESS IN COMMAND LINE PARAMETERS#

# Import all the libraries
import urllib, json
import sys, time, os
import arcpy
arcpy.CheckOutExtension("Spatial")
from arcpy.sa import *
import tkinter as tk
import matplotlib.pyplot as plt
import numpy as np

#Setup working environment
workarea= sys.argv[1]
os.chdir(workarea)
arcpy.env.workspace = workarea

#The tool lets you select the state of your study and gererates a flood risk map based on current guage water level##

# List of all the states to select from
OptionList = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA",
              "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
              "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
              "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
              "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]

# Set GUI parameters and specify interface for state selection
app = tk.Tk()
app.geometry('100x200')
variable = tk.StringVar(app)
variable.set(OptionList[0])
opt = tk.OptionMenu(app, variable, *OptionList)
opt.config(width=90, font=('Helvetica', 12))
opt.pack(side="top")
labelTest = tk.Label(text="select a state", font=('Helvetica', 12), fg='red')
labelTest.pack(side="top")
def callback(*args):
    labelTest.configure(text="The selected state is {}".format(variable.get()))
variable.trace("w", callback)
app.mainloop()

selectstate = variable.get()
selectstate = selectstate.lower()

# Setup URL objects for extracting data from USGS water watch web services
prefix = "https://waterwatch.usgs.gov/webservices/flood?"
region = "&region="+ selectstate
form = "&format=json"
url = prefix+region+form
wwresp = urllib.urlopen(url)
jresp =json.loads(wwresp.read())

#output is in from of json object with lat-long, station name, water level and comparison of current water level with water level over time
# Create an empty list that will store th outputs from json object
dataout =[]
# Store outputs to mpty list
for location in jresp["sites"]:
    station_name = location["station_nm"]
    long = location["dec_long_va"]
    lat= location["dec_lat_va"]
    class_percent = location["class"]
    percentile = location["percentile"]
    newloc = [station_name,lat,long,class_percent, percentile]
    dataout.append(newloc)

#asign spatial refrence file
sref = arcpy.SpatialReference(4326)
# Create a feature class with field to store points
temp_fc= arcpy.CreateFeatureclass_management(workarea,"points_json","POINT","","","",sref)
arcpy.MakeFeatureLayer_management(temp_fc,"temp")
arcpy.AddField_management(temp_fc,"name","TEXT")
arcpy.AddField_management(temp_fc,"value","FLOAT")

#Using Insert Cursor add points to the new feature class
cursor = arcpy.da.InsertCursor(temp_fc,["SHAPE@","name","value"])
for point in dataout:
    cursor.insertRow([arcpy.Point(point[2], point[1]), point[0],point[4]])
del cursor
del point
input_point ="points_json.shp"

# Interpolate the point file using Kriging technique in spatial analyst
krig_ras=arcpy.sa.Kriging (input_point, "value", "CIRCULAR")
krig_ras.save("krig.tif")

# Interpolate the point file using IDW technique in spatial analyst
idw_ras = arcpy.sa.Idw(input_point,"value")
idw_ras.save("idw.tif")

rasterlist =["krig.tif","idw.tif"]
krigstat = []
idwstat =[]
#Reclassify the raster file to HIGH, LOW and MODERATE Risk Level
for raster in rasterlist:
    remap = RemapRange([[0,50,1],[50,75,2],[75,100,3]])
    reclass = Reclassify(raster,"Value",remap,"NODATA")
    reclassname= "rc_"+raster
    reclass.save(reclassname)
    rc_raster = reclassname

    High_risk= 0
    Moderate_risk= 0
    Low_risk= 0

    # Counting the number of cells in each risk category
    with arcpy.da.SearchCursor(rc_raster,['Value','Count']) as cursor:
        for row in cursor:
            if row[0]==3:
                High_risk=row[1]
            elif row[0]==2:
                Moderate_risk =row[1]
            else:
                Low_risk =row[1]
    del cursor
    del row

    #print High_risk, Moderate_risk, Low_risk
    total = High_risk+Moderate_risk+Low_risk
    highRiskarea = (High_risk/total)*100
    moderateRiskarea = (Moderate_risk/total)*100
    lowRiskarea = (Low_risk/total)*100
    if raster =="krig.tif":
        krigstat.append(highRiskarea)
        krigstat.append(moderateRiskarea)
        krigstat.append(lowRiskarea)
    else:
        idwstat.append(highRiskarea)
        idwstat.append(moderateRiskarea)
        idwstat.append(lowRiskarea)

# data to plot
n_category = 3

# create plot
fig, ax = plt.subplots()
index = np.arange(n_category)
bar_width = 0.35
opacity = 0.8

rects1 = plt.bar(index, krigstat, bar_width,
alpha=opacity,
color='orange',
label='Kriging')

rects2 = plt.bar(index + bar_width, idwstat, bar_width,
alpha=opacity,
color='green',
label='IDW')

#modify your graph interface
plt.xlabel('Risk Zone')
plt.ylabel('Percent of Area')
plt.title('Percent of area in Risk zones')
plt.xticks(index + bar_width, ('High Risk', 'Moderate Risk', 'Low Risk'))
plt.legend()

# plot your graph with cell values
plt.tight_layout()
plt.show()
