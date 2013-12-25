__author__ = 'glenn'
from config import tempZipDir, ConnStringDEM_DB
from gen_design.gdal_operations import GdalOperations
from waterProject import WaterProject
from app import models



if __name__ == '__main__':
    # cat = GdalOperations(tempZipDir, ConnStringDEM_DB)
    # cat.zip_it()
    # del cat
    wat = WaterProject()
    print wat.project_name
