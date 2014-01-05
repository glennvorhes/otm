__author__ = 'glenn'
from config import tempZipDir, ConnStringDEM_DB
from gen_design.gdal_operations import GdalOperations, GDAL_OPERATIONS_ARRAYS
from geoalchemy2 import functions as geoalchemy_func

from app import models, DatabaseSessionMaker
# from waterProject import WaterProject
# from app import models
from sqlalchemy import func

if __name__ == '__main__':
    db_session = DatabaseSessionMaker()
    project = db_session.query(models.Project).get(1)
    print dir(project.geom)
    print dir(project.geom.srid)
    print db_session.scalar(geoalchemy_func.ST_AsText(project.geom.ST_Transform(4326)))
    keys = dir(project)
    for key in keys:
        assert(isinstance(key, str))
        if key.startswith('__'):
            continue
        print key
    db_session.close()
    # db_session.scalar(func.)


    exit()

    # cat = GdalOperations(tempZipDir, ConnStringDEM_DB)
    # cat.zip_it()
    # del cat
    
    input_args = {"in_srid": 4326, "out_srid": 3857, "geom_wkt": "POLYGON((-70.85935206854856 \
19.65229329611083,-70.86184115851442 19.642512431567376,-70.84410505140411 19.622975442\
353933,-70.83243207777102 19.63558690585363,-70.83549113715243 19.645745841173618,-70.846\
56329596567 19.65140415124034,-70.85935206854856 19.65229329611083))"}
    gdal_ops = GdalOperations(tempZipDir, ConnStringDEM_DB)
    gdal_ops.image_from_database(**input_args)
    gdal_ops.make_image_warp(cell_size=5)
    print gdal_ops.get_coords_from_index(150, 150)
    print gdal_ops.get_array_value(150, 150, GDAL_OPERATIONS_ARRAYS.DEM_VALUE)
    print gdal_ops.get_raster_dimensions()
    print gdal_ops.get_raster_extent()


    print 'here'

    # wat = WaterProject()
    # print wat.project_name
