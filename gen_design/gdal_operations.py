import os
import uuid
from osgeo import gdal, gdalconst
import psycopg2
from subprocess import Popen
import string
import shutil
from math import floor
import sys


class GDAL_OPERATIONS_PROPS:
    DEM_RAW = 0
    DEM_RESAMPLE = 1
    HILLSHADE = 2
    HILLSHADE_TRANSPARENT = 3
    COLOR_GRADIENT = 4
    ZIP_FILE = 5

    
class GDAL_OPERATIONS_ARRAYS:
    DEM_VALUE = 'DEM'
    SLOPE_VALUE = 'SLOPE'
    ASPECT_VALUE = 'ASPECT'
    


class GdalOperations(object):
    """Class to handle all GDAL image operations

    Constructor takes the temp folder root and database
    connection string as parameters
    Creates the new temp directories and paths to
    output images within it.
    """
    def __init__(self, temp_folder_root, connection_string):
        #Save reference to the connection string
        self.db_connection_string = connection_string

        #Path to the unique directory within the temp directories folder
        self.__unique_temp_directory = os.path.join(temp_folder_root, str(uuid.uuid1()))
        os.makedirs(self.__unique_temp_directory)
        self.__dem_image_folder = os.path.join(self.__unique_temp_directory, 'demDownload')
        os.makedirs(self.__dem_image_folder)
        self.__dem_zip_file = self.__dem_image_folder + '.zip'

        self.__dem_tif_path = os.path.join(self.__dem_image_folder, 'dem_raw_resolution.tif')
        self.__dem_tif_resample_path = os.path.join(self.__dem_image_folder, 'dem_resample.tif')
        self.__hillshade_png_path = os.path.join(self.__dem_image_folder, 'hillshade.png')
        self.__slope_tif_path = os.path.join(self.__dem_image_folder, 'slope.tif')
        self.__aspect_tif_path = os.path.join(self.__dem_image_folder, 'aspect.tif')
        self.__hillshade_transparent_png_path = os.path.join(
            self.__dem_image_folder, 'hillshade_transparent.png')
        self.__color_gradient_png_path = os.path.join(self.__dem_image_folder, 'color_gradient.png')
        self.__color_gradient_txt_path = os.path.join(self.__dem_image_folder, 'color.txt')

        self.__image_paths = {
            GDAL_OPERATIONS_ARRAYS.DEM_VALUE: self.__dem_tif_resample_path,
            GDAL_OPERATIONS_ARRAYS.ASPECT_VALUE: self.__aspect_tif_path,
            GDAL_OPERATIONS_ARRAYS.SLOPE_VALUE: self.__slope_tif_path
        }

        #Flags to check if images have been made
        self.__base_image_made = \
            self.__resample_image_made = \
            self.__hillshade_made = \
            self.__transparent_hillshade_made = \
            self.__color_gradient_made = \
            self.__zip_file_made = \
            self.__aspect_made = \
            self.__slope_made = False

        self.__geotransform = None
        self.__projection = None
        self.__cols = None
        self.__rows = None

        self.__array_read = {
            GDAL_OPERATIONS_ARRAYS.DEM_VALUE: False,
            GDAL_OPERATIONS_ARRAYS.ASPECT_VALUE: False,
            GDAL_OPERATIONS_ARRAYS.SLOPE_VALUE: False
        }

        self.__data_arrays = {
            GDAL_OPERATIONS_ARRAYS.DEM_VALUE: None,
            GDAL_OPERATIONS_ARRAYS.ASPECT_VALUE: None,
            GDAL_OPERATIONS_ARRAYS.SLOPE_VALUE: None
        }



    def image_from_database(self, geom_wkt, in_srid, out_srid):
        """
        Create an on disk image representing the contents of the database

        Given an input wkt and srid and an output srid, get the image from the
        database, turn it into a float, and save the image to dsik using the
        vsimem dataset as an intermediary
        """
        is_geom_valid = True

        if not in_srid == 4326:
            return 'only SRID 4326 is currently supported'

        conn = psycopg2.connect(self.db_connection_string)
        cur = conn.cursor()

        try:
            cur.execute("select ST_IsValid(ST_GeomFromText('{0}',{1})) as isvalid, \
                        ST_Area(ST_Transform(ST_GeomFromText('{0}',{1}),3857)) as area".format(geom_wkt, in_srid))
            result = cur.fetchone()
            is_geom_valid = bool(result[0])
            area = float(result[1])
        except psycopg2.Error:
            conn.close()
            del conn, cur
            is_geom_valid = False

        # Bail out if the geometry isn't valid
        if not is_geom_valid:
            return 'geom not valid'
        if area > 246952910:
            return 'geom too big'

        query = "SELECT \
                    ST_AsGDALRaster(\
                        ST_Transform(\
                            ST_Clip(\
                                ST_Union(rast),ST_GeomFromText('{0}', {1}),\
                            true),\
                        {2}),\
                    'GTiff')\
                    FROM aster_gdem \
                    WHERE ST_Intersects(\
                        rast, ST_GeomFromText('{0}', {1})\
                    );".format(geom_wkt, in_srid, out_srid)

        cur.execute(query)
        img_buffer = cur.fetchone()[0]
        conn.close()

        # create the in memory image
        in_memory_img_path = os.path.join('/vsimem', str(uuid.uuid1()))
        gdal.FileFromMemBuffer(in_memory_img_path, str(img_buffer))

        # Open the in-memory file
        database_out_png_dataset = gdal.Open(in_memory_img_path)

        if database_out_png_dataset is None:
            return 'Could not open'

        cols = database_out_png_dataset.RasterXSize
        rows = database_out_png_dataset.RasterYSize
        # num_bands = database_out_png_dataset.RasterCount

        data_red = database_out_png_dataset.GetRasterBand(1).ReadAsArray(0, 0, cols, rows)
        data_grn = database_out_png_dataset.GetRasterBand(2).ReadAsArray(0, 0, cols, rows)
        data_blu = database_out_png_dataset.GetRasterBand(3).ReadAsArray(0, 0, cols, rows)

        dem_dataset = gdal.GetDriverByName('GTiff').Create(self.__dem_tif_path, cols, rows, 1, gdalconst.GDT_Float32)

        # green numpy array as float
        data_float = data_grn.astype(float)

        # Add values from red and blue bands with appropriate conversion
        data_float += data_red * 256.0 + data_blu / 256.0

        # write the array to the band and flush statistics
        out_band1 = dem_dataset.GetRasterBand(1)
        out_band1.WriteArray(data_float, 0, 0)
        out_band1.SetNoDataValue(0)
        out_band1.FlushCache()
        out_band1.GetStatistics(0, 1)

        # set the geotransform and projection
        dem_dataset.SetGeoTransform(database_out_png_dataset.GetGeoTransform())
        dem_dataset.SetProjection(database_out_png_dataset.GetProjection())

        # unlink the in memory dataset and set open variables to None
        gdal.Unlink(in_memory_img_path)
        database_out_png_dataset = None
        dem_dataset = None
        out_band1 = None

        # Flag the base image as made
        self.__base_image_made = True

    def make_image_warp(self, cell_size=10):
        if not self.__base_image_made:
            raise Exception
            return False, 'Base image not created'

        warp_process_args = 'gdalwarp \
                    -dstnodata 0 \
                    -tr {2} {2} \
                    -r cubicspline \
                    -overwrite \
                    -multi \
                    -wm 1000 \
                    -co "TILED=YES" \
                    {0} {1}'.format(self.__dem_tif_path, self.__dem_tif_resample_path, cell_size)

        # run warp/resampling process
        warp_process = Popen(warp_process_args, shell=True)
        warp_process.wait()
        self.__resample_image_made = True

    def make_color_gradient(self):
        if not self.__resample_image_made:
            self.make_image_warp()

        color_ramp = [
            '100% white',
            '90% grey',
            '80% blue',
            '70% aqua',
            '60% green',
            '50% yellow',
            '40% orange',
            '30% brown',
            '20% purple',
            '10% indigo',
            '0% magenta',
            'nv 0 0 0 0']

        color_ramp = [
            '100% white',
            '83% grey',
            '67% brown',
            '50% orange',
            '33% green',
            '17% yellow',
            '0% aqua',
            'nv 0 0 0 0']

        with open(self.__color_gradient_txt_path, 'w') as f:
                f.write(string.join(color_ramp, '\n'))

         # Make the color gradient
        color_gradient_process_args = 'gdaldem color-relief -of PNG -alpha {0} {1} {2}'.\
            format(self.__dem_tif_resample_path,
                   self.__color_gradient_txt_path,
                   self.__color_gradient_png_path)

        color_gradient_process = Popen(color_gradient_process_args, shell=True)

        # Be sure the color gradient process has
        color_gradient_process.wait()
        self.__color_gradient_made = True

    def make_hillshade(self):
        if not self.__resample_image_made:
            self.make_image_warp()

        # make the hillshade
        hillshade_process_args = 'gdaldem hillshade {0} {1} -of PNG -z 5'.format(
            self.__dem_tif_resample_path, self.__hillshade_png_path)

        hillshade_process = Popen(hillshade_process_args, shell=True)

        hillshade_process.wait()

        self.__hillshade_made = True

    def make_slope(self):
        if not self.__resample_image_made:
            self.make_image_warp()

        slope_process_args = 'gdaldem slope {0} {1} -p'.format(
            self.__dem_tif_resample_path, self.__slope_tif_path)

        slope_process = Popen(slope_process_args, shell=True)
        slope_process.wait()

        self.__slope_made = True

    def make_aspect(self):
        if not self.__resample_image_made:
            self.make_image_warp()

        aspect_process_args = 'gdaldem aspect {0} {1} -zero_for_flat'.format(
            self.__dem_tif_resample_path, self.__aspect_tif_path)

        aspect_process = Popen(aspect_process_args, shell=True)
        aspect_process.wait()

        self.__aspect_made = True

    def make_transparent_hillshade(self):
        if not self.__resample_image_made:
            self.make_image_warp()

        from PIL import Image as PImage
        from PIL import ImageOps

        # Load the source file
        src = PImage.open(self.__dem_tif_resample_path)

        # Convert to single channel
        grey = ImageOps.grayscale(src)

        # Make negative image
        neg = ImageOps.invert(grey)

        # Split channels
        bands = neg.split()

        # Create a new (black) image
        black = PImage.new('RGBA', src.size)

        # Copy inverted source into alpha channel of black image
        black.putalpha(bands[0])

        # Return a pixel access object that can be used to read and modify pixels
        pixdata = black.load()

        # Loop through image data
        for y in xrange(black.size[1]):
            for x in xrange(black.size[0]):
                # Replace black pixels with pure transparent
                if pixdata[x, y] == (0, 0, 0, 255):
                    pixdata[x, y] = (0, 0, 0, 0)
                # Lighten pixels slightly
                else:
                    a = pixdata[x, y]
                    pixdata[x, y] = a[:-1] + (a[-1]-74,)

        # Save as PNG
        black.save(self.__hillshade_transparent_png_path, "png")
        self.__transparent_hillshade_made = True

    def zip_it(self):
        shutil.make_archive(self.__dem_image_folder, format="zip", root_dir=self.__dem_image_folder)
        self.__zip_file_made = True

    def get_file_path(self, prop):
        """
        Get one of the properties defined by the class GDAL_OPERATIONS_PROPS in this module
        """
        if prop == GDAL_OPERATIONS_PROPS.DEM_RAW:
            if not self.__base_image_made:
                return None
            return self.__dem_tif_path
        elif prop == GDAL_OPERATIONS_PROPS.DEM_RESAMPLE:
            if not self.__resample_image_made:
                self.make_image_warp()
            return self.__dem_tif_resample_path
        elif prop == GDAL_OPERATIONS_PROPS.HILLSHADE:
            if not self.__hillshade_made:
                self.make_hillshade()
            return self.__hillshade_png_path
        elif prop == GDAL_OPERATIONS_PROPS.HILLSHADE_TRANSPARENT:
            if not self.__transparent_hillshade_made:
                self.make_transparent_hillshade()
            return self.__hillshade_transparent_png_path
        elif prop == GDAL_OPERATIONS_PROPS.COLOR_GRADIENT:
            if not self.__color_gradient_made:
                self.make_color_gradient()
            return self.__color_gradient_png_path
        elif prop == GDAL_OPERATIONS_PROPS.ZIP_FILE:
            if not self.__zip_file_made:
                self.zip_it()
            return self.__dem_zip_file

    def __check_raise_index_error(self, row, column):
        if row > self.__rows - 1 or column > self.__cols - 1:
            raise IndexError('Valid values, 0 <= rows <= ' + str(self.__rows - 1)
                             + ', 0 <= columns <= ' + str(self.__cols - 1))

    def get_coords_from_index(self, row, column):
        if self.__geotransform is None:
            self.__read_as_array(GDAL_OPERATIONS_ARRAYS.DEM_VALUE)
        self.__check_raise_index_error(row, column)

        upper_left_x = self.__geotransform[0]
        w_e_resolution = self.__geotransform[1]

        upper_left_y = self.__geotransform[3]

        #negative values
        n_s_resolution = self.__geotransform[5]

        upper_left_pixel_center = {
            'upperLeftX': upper_left_x + w_e_resolution / 2,
            'upperLeftY': upper_left_y + n_s_resolution / 2
        }

        x = upper_left_pixel_center['upperLeftX'] + column * w_e_resolution
        y = upper_left_pixel_center['upperLeftY'] + row * n_s_resolution

        return x, y

    def get_index_from_coords(self, x, y):
        min_x = self.__geotransform[0]
        w_e_resolution = self.__geotransform[1]
        max_x = min_x + w_e_resolution * self.__cols

        max_y = self.__geotransform[3]
        #negative values
        n_s_resolution = self.__geotransform[5]
        min_y = max_y + n_s_resolution * self.__rows

        if x < min_x or x > max_x or y < min_y or y > max_y:
            raise ValueError('Valid Values, ' + str(round(min_x, 2)) + " <= X <= " + str(round(max_x, 2)) + ', ' +
                             str(round(min_y, 2)) + " <= Y <= " + str(round(max_y, 2)))

#        Get row, remember this is reversed, top left is 0,0
        r = int(floor((y - max_y) / n_s_resolution))
        c = int(floor((x - min_x) / w_e_resolution))
        return r, c

    def get_array_value(self, row, column, imageid):
        if not self.__array_read[imageid]:
            self.__read_as_array(imageid)
        self.__check_raise_index_error(row, column)
        return self.__data_arrays[imageid][row, column]

    def __read_as_array(self, imageid):
        if imageid == GDAL_OPERATIONS_ARRAYS.DEM_VALUE and not self.__resample_image_made:
            self.make_image_warp()
        elif imageid == GDAL_OPERATIONS_ARRAYS.ASPECT_VALUE and not self.__aspect_made:
            self.make_aspect()
        elif imageid == GDAL_OPERATIONS_ARRAYS.SLOPE_VALUE and not self.__slope_made:
            self.make_slope()

        dataset = gdal.Open(self.__image_paths[imageid], gdalconst.GA_ReadOnly)
        if dataset is None:
            print 'Could not open ' + os.path.basename(self.__image_paths[imageid])
            raise

        self.__cols = dataset.RasterXSize
        self.__rows = dataset.RasterYSize

        self.__geotransform = dataset.GetGeoTransform()
        self.__projection = dataset.GetProjection()

        band = dataset.GetRasterBand(1)

        self.__data_arrays[imageid] = band.ReadAsArray(0, 0, self.__cols, self.__rows)

        self.__array_read[imageid] = True

        dataset = None

    def get_raster_dimensions(self):
        if self.__geotransform is None:
            self.__read_as_array(GDAL_OPERATIONS_ARRAYS.DEM_VALUE)
        return 'rows: {0}, columns {1}'.format(self.__rows, self.__cols)

    def get_raster_extent(self):
        if self.__geotransform is None:
            self.__read_as_array(GDAL_OPERATIONS_ARRAYS.DEM_VALUE)
        min_x = self.__geotransform[0]
        w_e_resolution = self.__geotransform[1]
        max_x = min_x + w_e_resolution * self.__cols

        max_y = self.__geotransform[3]
        #negative values
        n_s_resolution = self.__geotransform[5]
        min_y = max_y + n_s_resolution * self.__rows

        return "Min X: {0}, Min Y: {1}, Max X: {2}, Max Y: {3}".format(min_x, min_y, max_x, max_y)

