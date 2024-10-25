# code: utf-8
# author: Xudong Zheng
# email: z786909151@163.com
import geopandas as gpd
import numpy as np
import pandas as pd
import os
import shapely
import math
from ..tools.utilities import createBoundaryShp


class Basins(gpd.GeoDataFrame):

    def __add__(self, basins):
        pass

    def __sub__(self, basins):
        pass

    def __and__(self, basins):
        pass


class Grids(gpd.GeoDataFrame):

    def __add__(self, grids):
        pass

    def __sub__(self, grids):
        pass

    def __and__(self, grids):
        pass


def intersectGridsWithBasins(grids: Grids, basins: Basins):
    intersects_grids_list = []
    intersects_grids = Grids()
    for i in basins.index:
        basin = basins.loc[i, "geometry"]
        intersects_grids_ = grids[grids.intersects(basin)]
        intersects_grids = pd.concat([intersects_grids, intersects_grids_], axis=0)
        intersects_grids_list.append(intersects_grids_)

    intersects_grids["grids_index"] = intersects_grids.index
    intersects_grids.index = list(range(len(intersects_grids)))
    droped_index = intersects_grids["grids_index"].drop_duplicates().index
    intersects_grids = intersects_grids.loc[droped_index, :]

    basins["intersects_grids"] = intersects_grids_list
    return basins, intersects_grids


class HCDNBasins(Basins):
    def __init__(self, home="E:\\data\\hydrometeorology\\CAMELS", data=None, *args, geometry=None, crs=None, **kwargs):
        HCDN_shp_path = os.path.join(home, "basin_set_full_res", "HCDN_nhru_final_671.shp")
        HCDN_shp = gpd.read_file(HCDN_shp_path)
        HCDN_shp["AREA_km2"] = HCDN_shp.AREA / 1000000  # m2 -> km2
        super().__init__(HCDN_shp, *args, geometry=geometry, crs=crs, **kwargs)


class HCDNGrids(Grids):
    def __init__(self, home, *args, data=None, geometry=None, crs=None, **kwargs):
        grid_shp_label_path = os.path.join(home, "map", "grids_0_25_label.shp")
        grid_shp_label = gpd.read_file(grid_shp_label_path)
        grid_shp_path = os.path.join(home, "map", "grids_0_25.shp")
        grid_shp = gpd.read_file(grid_shp_path)
        grid_shp["point_geometry"] = grid_shp_label.geometry
        
        super().__init__(grid_shp, *args, geometry=geometry, crs=crs, **kwargs)

    def createBoundaryShp(self):
        boundary_point_center_shp, boundary_point_center_x_y, boundary_grids_edge_shp, boundary_grids_edge_x_y = createBoundaryShp(self)
        return boundary_point_center_shp, boundary_point_center_x_y, boundary_grids_edge_shp, boundary_grids_edge_x_y


class Grids_for_shp(Grids):
    def __init__(self, gshp, *args,
                 cen_lons=None, cen_lats=None, stand_lons=None, stand_lats=None,
                 res=None, adjust_boundary=True, geometry=None, crs=None, **kwargs):
        """
        Grids (grid_shp) for a given gshp, it can be any gpd (basins, grids...)
        
        res=None, one grid for this shp (boundary grid)
        
        cen_lons: directly construct grids based on given cen_lons (do not consider gshp boundary)
        
        stand_lons: a series of stand_lons, larger than gshp's boundary, construct grids based on standard grids (clip based on gshp boundary)
        
        adjust_boundary: adjust boundary by res (res/2)
        
        """
        # get bound
        shp_bounds = gshp.loc[:, "geometry"].iloc[0].bounds
        boundary_x_min = shp_bounds[0]
        boundary_x_max = shp_bounds[2]
        boundary_y_min = shp_bounds[1]
        boundary_y_max = shp_bounds[3]
        
        # lambda function
        grid_polygon = lambda xmin, xmax, ymin, ymax: shapely.geometry.Polygon([(xmin, ymax), (xmax, ymax), (xmax, ymin), (xmin, ymin)])
        grid_point = lambda x, y: shapely.geometry.Point(x, y)
        
        # create grid_shp
        grid_shp = gpd.GeoDataFrame()
        
        if res:
            # construct grids based on given cen_lons: do not consider gshp boundary
            if cen_lons is not None: # *note: len(cen_lons) == len(cen_lats)
                grid_shp.loc[:, "geometry"] = [grid_polygon(cen_lons[i]-res/2, cen_lons[i]+res/2, cen_lats[i]-res/2, cen_lats[i]+res/2) for i in range(len(cen_lats))]
                grid_shp.loc[:, "point_geometry"] = [grid_point(cen_lons[i], cen_lats[i]) for i in range(len(cen_lats))]
            
            # construct grids based on standard grids: clip based on gshp boundary
            elif stand_lons is not None:
                
                cen_lons = stand_lons[np.where(stand_lons - res/2 <= boundary_x_min)[0][-1]: np.where(stand_lons + res/2 >= boundary_x_max)[0][0] + 1]
                cen_lats = stand_lats[np.where(stand_lats - res/2 <= boundary_y_min)[0][-1]: np.where(stand_lats + res/2 >= boundary_y_max)[0][0] + 1]
                
                cen_lons, cen_lats = np.meshgrid(cen_lons, cen_lats)
                cen_lons = cen_lons.flatten()
                cen_lats = cen_lats.flatten()
                
                grid_shp.loc[:, "geometry"] = [grid_polygon(cen_lons[i]-res/2, cen_lons[i]+res/2, cen_lats[i]-res/2, cen_lats[i]+res/2) for i in range(len(cen_lats))]
                grid_shp.loc[:, "point_geometry"] = [grid_point(cen_lons[i], cen_lats[i]) for i in range(len(cen_lats))]

            # construct grids based on boundary
            else:
                if adjust_boundary:
                    boundary_x_min = math.floor(boundary_x_min / res) * res
                    boundary_x_max = math.ceil(boundary_x_max / res) * res
                    boundary_y_min = math.floor(boundary_y_min / res) * res
                    boundary_y_max = math.ceil(boundary_y_max / res) * res
                
                cen_lons = np.arange((boundary_x_min + res/2), (boundary_x_max), res)
                cen_lats = np.arange((boundary_y_min + res/2), (boundary_y_max), res)

                # cen_lons = np.arange(math.floor((boundary_x_min + res/2) / (res/2)) * (res/2), math.ceil((boundary_x_max + res/2) / (res/2)) * (res/2), res)
                # cen_lats = np.arange(math.floor((boundary_y_min + res/2) / (res/2)) * (res/2), math.ceil((boundary_y_max + res/2) / (res/2)) * (res/2), res)

                cen_lons, cen_lats = np.meshgrid(cen_lons, cen_lats)
                cen_lons = cen_lons.flatten()
                cen_lats = cen_lats.flatten()
                
                grid_shp.loc[:, "geometry"] = [grid_polygon(cen_lons[i]-res/2, cen_lons[i]+res/2, cen_lats[i]-res/2, cen_lats[i]+res/2) for i in range(len(cen_lats))]
                grid_shp.loc[:, "point_geometry"] = [grid_point(cen_lons[i], cen_lats[i]) for i in range(len(cen_lats))]
        
        # res=None, one grid for this shp (boundary grid)
        else:
            grid_shp.loc[0, "geometry"] = grid_polygon(boundary_x_min, boundary_x_max, boundary_y_min, boundary_y_max)
            grid_shp.loc[0, "point_geometry"] = grid_point((boundary_x_min + boundary_x_max)/2, (boundary_y_min + boundary_y_max)/2)
        
        grid_shp = grid_shp.set_geometry("point_geometry")
        crs = crs if crs is not None else "EPSG:4326"
        grid_shp = grid_shp.set_crs(crs)
        
        super().__init__(grid_shp, *args, geometry=geometry, crs=crs, **kwargs)
    
    def createBoundaryShp(self):
        boundary_point_center_shp, boundary_point_center_x_y, boundary_grids_edge_shp, boundary_grids_edge_x_y = createBoundaryShp(self)
        return boundary_point_center_shp, boundary_point_center_x_y, boundary_grids_edge_shp, boundary_grids_edge_x_y


def createGridForBasin(basin_shp, grid_res):
    grid_shp = Grids_for_shp(basin_shp, res=grid_res, adjust_boundary=True)
    
    grid_shp_lon = grid_shp.point_geometry.x.to_list()
    grid_shp_lat = grid_shp.point_geometry.y.to_list()
    
    return grid_shp_lon, grid_shp_lat, grid_shp


def read_one_basin_shp(basin_index, home="E:\\data\\hydrometeorology\\CAMELS"):
    basin_shp_all = HCDNBasins(home)
    basin_shp = basin_shp_all.loc[basin_index: basin_index, :]
    return basin_shp_all, basin_shp