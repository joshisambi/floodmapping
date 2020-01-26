#------------ FLOOD RISK MAPPING -----------#

# # --- AUTHOR: Sambhavi Joshi --- # #

####################################################################

#PLEASE SET YOUR WORKING SPACE BY PUTTING THE ADDRESS IN COMMAND LINE PARAMETERS#

#import all your packages
import arcpy
import sys,time,os

# Set your working dictionary
workarea = sys.argv[1]
os.chdir(workarea)
arcpy.env.workspace = workarea

#import all functions from spatial analyst
arcpy.CheckOutExtension("Spatial")
from arcpy.sa import *

# set raster cell size and procession extents
arcpy.env.cellSize = 30
arcpy.env.extent = "-85.212343 29.298130 -81.212427 30.825174"
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(4326)

# Combine all DEMs into one raster
#This part of the code was not working
# I kept geting error 999999
rasters = []
location = "C:\\temp\\programming\\inputs\\dem"
walk = arcpy.da.Walk(location, topdown=True, datatype="RasterDataset")
for dirpath, dirnames, filenames in walk:
    for filename in filenames:
        rasters.append(os.path.join(dirpath, filename))
ras_list = ";".join(rasters)
mosaicDEM = workarea
arcpy.MosaicToNewRaster_management(ras_list,mosaicDEM,"comb_DEM", "", "16_BIT_UNSIGNED","30","1","LAST","FIRST")


# mask the mosaic DEM to study area
DEM = "comb_dem1.tif"
project_area = "project_area.shp"
extractMask = ExtractByMask(DEM,project_area)
extractMask.save("clip_DEM.tif")

surface = "clip_DEM.tif"

#generate slope from DEM
outSlope = Slope("clip_DEM.tif","PERCENT_RISE") #This function might not work # So i have put slope raster in the input folder
outSlope.save('slope_clip')

# create flow direction raster
dir_ras = 'dir_ras'
FlowDirection(surface)
flowDirection.save(dir_ras)

# Calculate flow accumulation
flow_accum = 'flow_accum'
flowAccumulation = FlowAccumulation(dir_ras,"","FLOAT")
flowAccumulation.save(flow_accum)

#create buffer around water bodies
distance = [5,10,20,50]
rivers_all = "river_florida.shp"
river_buf = "river_buffer.shp"
arcpy.MultipleRingBuffer_analysis(rivers_all,river_buf,distance,"miles","","ALL")

# clip waterbodies to extent
rivers = "riversbuf_clip.shp"
arcpy.Clip_analysis(river_buf, project_area, rivers)

#convert buffer distance to raster data
river_raster = "river_raster.tif"
field = "distance"
arcpy.FeatureToRaster_conversion(rivers,field,river_raster)

#clip precipitation to study area
precip_fl = "precip1981_2010_a_fl.shp"
precip = "precip_clip.shp"
arcpy.Clip_analysis(precip_fl,project_area,precip)

#convert precipitation to rater data
precip_raster = "precip_raster.tif"
field = "PrecipInch"
arcpy.FeatureToRaster_conversion(precip,field,precip_raster)

#clip past flood event to study area
flood08_shp = "flood_clip08.shp"
flood12_shp = "flood_clip12.shp"
arcpy.Clip_analysis("flood_2008.shp",project_area,flood08_shp)
arcpy.Clip_analysis("flood_2012.shp",project_area,flood12_shp)

#convert past flood event to raster data
flood08 = "flood08.tif"
flood12 = "flood12.tif"
field = "gridcode"
arcpy.FeatureToRaster_conversion(flood08_shp,field,flood08)
arcpy.FeatureToRaster_conversion(flood12_shp,field,flood12)

#Clip landcover to study area
landcover = "landcover_clip.tif"
arcpy.Clip_management("nlcd_fl_utm17.tif","-85.212343 29.298130 -81.212427 30.825174",landcover, project_area)
extractMask = ExtractByMask("nlcd_fl_utm17.tif",project_area)
extractMask.save(landcover)

# reclassify and  assign weight for slope layer
slope = 'slope'
slopeweigh = int(raw_input('\n *Please make sure that sum of all the weights is 100* \nAssign percent weight for slope layer'))
remapslope =RemapRange([[0,1.8,5],[1.8,4.6,4],[4.6,8.3,3],[8.3,13.8,2],[13.8,117.8,1]])

# reclassify and  assign weight for flow accumulation layer
flow_accum = "flow_accum"
flowweigh = int(raw_input('\n Assign percent weight for flowccumulation layer'))
remapflowaccum = RemapRange([[0,1500000,1],[1500000,2500000,2],[2500000,4000000,3],[4000000,5000000,4],[5000000,6500000,5]])

# reclassify and  assign weight for landcover layer
landcover = "landuse_clip"
landweigh= int(raw_input('\n Assign percent weight for landcover layer'))
remaplandcover = RemapValue([["Open Water","NODATA"],["Developed, Open Space", 1],["Developed, Low Intensity", 2],["Developed, Medium Intensity", 2],["Developed, High Intensity",3],["Barren Land",1],["Deciduous Forest",1],["Evergreen Forest", 1],["Mixed Forest",1],["Shrub/Scrub",1],["Herbaceuous",1],["Hay/Pasture",1],["Cultivated Crops",1],["Woody Wetlands",1],["Emergent Herbaceuous Wetlands",1]])

# reclassify and  assign weight for precipitation layer
precipitation = precip_raster
precipweigh = int(raw_input('\n Assign percent weight for precipitation layer'))
remapprecip = RemapRange([[46,50,1],[50,55,2],[55,60,3],[60,63,4]])

# reclassify and  assign weight for distance from river layer
riverbuffer = river_raster
riverweigh = int(raw_input('\n Assign percent weight for river buffer layer'))
remapbuff =RemapValue([[5,4],[10,3],[20,2],[50,1]])

flood08 = flood08
flood12 = flood12

# reclassify and  assign weight for flood layer
remapflood = RemapRange([[1,8,1],[8,16,3],[16,26,5]])
floodweigh = int(raw_input('\n Assign percent weight for past flood layer'))

weightsum = slopeweigh + flowweigh + landweigh + precipweigh + riverweigh + floodweigh
if weightsum != 100:
    print "Sum of all the layer weights is not 100."
else:

    weight_table = WOTable([[slope, slopeweigh, "VALUE", remapslope],
                            [flow_accum, flowweigh,"VALUE", remapflowaccum],
                            [landcover,landweigh,"LAND_COVER",remaplandcover],
                            [precipitation,precipweigh,"VALUE",remapprecip],
                            [riverbuffer,riverweigh,"VALUE", remapbuff],
                            [flood08, floodweigh, "Value", remapflood],
                            [flood08, floodweigh, "Value", remapflood]], [1,5,1])

    weightedoverlay = WeightedOverlay(weight_table)
    weightedoverlay.save("overlay")

##    slope_re = Reclassify(slope,"Value",remapslope,"NODATA")
##    slope_reweight = (slope_re)*slopeweigh
##    slope_reweight.save("slope_reweight.tif")
##    slope_reweight = "slope_reweight.tif"
##
##    flow_re = Reclassify(flow_accum,"VALUE",remapflowaccum,"NODATA")
##    flow_reweight = (flow_re)*flowweigh
##    flow_reweight.save("flow_reweight.tif")
##    flow_reweight = "flow_reweight.tif"
##
##    land_re = Reclassify(landcover,"LAND_COVER",remaplandcover,"NODATA")
##    land_reweight = (land_re)*landweigh
##    land_reweight.save("land_reweight.tif")
##    land_reweight = "land_reweight.tif"
##
##    precip_re = Reclassify(precip,"VALUE",remapprecip,"NODATA")
##    precip_reweight = (precip_re)*precipweigh
##    slope_reweight.save("slope_reweight.tif")
##    slope_reweight = "slope_reweight.tif"
##    river_re = Reclassify(riverbuffer,"VALUE",remapbuff,"NODATA")
##    river_reweight = (river_re)*riverweigh
##    slope_reweight.save("slope_reweight.tif")
##    slope_reweight = "slope_reweight.tif"
##    flood08_re = Reclassify(flood08,"Value",remapflood,"NODATA")
##    flood08_reweight = (flood08_re)*floodweigh
##    slope_reweight.save("slope_reweight.tif")
##    slope_reweight = "slope_reweight.tif"
##
##    flood12_re = Reclassify(flood12,"Value",remapflood,"NODATA")
##    flood12_reweight = (flood12_re)*floodweigh
##    slope_reweight.save("slope_reweight.tif")
##    slope_reweight = "slope_reweight.tif"
##    comb_weigh = slope_reweight + flow_reweight + land_reweight + precip_reweight + flood08_reweight + flood12_reweight
##    comb = comb_weigh/100
##    comb.save("overlay.tif")


