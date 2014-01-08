__author__ = 'glenn'
from geoalchemy2 import functions as geoalchemy_func
from app import models, DatabaseSessionMaker
from config import tempZipDir, ConnStringDEM_DB
from gen_design.gdal_operations import GdalOperations, GDAL_OPERATIONS_ARRAYS


class GenericProject(object):

    def __init__(self, project_id):
        """


        """
        assert(isinstance(project_id, int))

        self.feature_list = []

        db_session = DatabaseSessionMaker()
        self.project_object = db_session.query(models.Project).get(project_id)

        assert(isinstance(self.project_object, models.Project))

        feats = self.project_object.features

        self.project_type_object = db_session.query(models.Project_Type).get(self.project_object.tid)

        for feat in feats:
            print db_session.scalar(geoalchemy_func.ST_AsText(feat.geom))
            self.feature_list.append(feat)

        assert(isinstance(self.project_type_object, models.Project_Type))

        self.__extent_geometry_text = db_session.scalar(geoalchemy_func.ST_AsText(
            self.project_object.geom.ST_Transform(4326)))

        db_session.close()
        self.create_dem()

    def create_dem(self):

        input_args = {"in_srid": 4326,
                      "out_srid": self.project_object.geom.srid,
                      "geom_wkt": self.__extent_geometry_text}

        gdal_ops = GdalOperations(tempZipDir, ConnStringDEM_DB)
        gdal_ops.image_from_database(**input_args)
        gdal_ops.make_image_warp(cell_size=3)
        print gdal_ops.get_coords_from_index(150, 150)
        print gdal_ops.get_array_value(150, 150, GDAL_OPERATIONS_ARRAYS.DEM_VALUE)
        print gdal_ops.get_raster_dimensions()
        print gdal_ops.get_raster_extent()





