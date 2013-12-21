from flask import render_template, request, send_file
from app import app
import psycopg2
from config import ConnStringDEM_DB
import base64
import os
import uuid
import shutil
from osgeo import gdal, gdalconst
from subprocess import Popen
from datetime import datetime, timedelta
from config import basedir, tempZipDir
import thread

# import io
# from PIL import Image as PImage
# from PIL import ImageOps
# def make_transparent_hillshade(input_file, output_file):
#     # Load the source file
#     src = PImage.open(input_file)
#
#     # Convert to single channel
#     grey = ImageOps.grayscale(src)
#
#     # Make negative image
#     neg = ImageOps.invert(grey)
#
#     # Split channels
#     bands = neg.split()
#
#     # Create a new (black) image
#     black = PImage.new('RGBA', src.size)
#
#     # Copy inverted source into alpha channel of black image
#     black.putalpha(bands[0])
#
#     # Return a pixel access object that can be used to read and modify pixels
#     pixdata = black.load()
#
#     # Loop through image data
#     for y in xrange(black.size[1]):
#         for x in xrange(black.size[0]):
#             # Replace black pixels with pure transparent
#             if pixdata[x, y] == (0, 0, 0, 255):
#                 pixdata[x, y] = (0, 0, 0, 0)
#             # Lighten pixels slightly
#             else:
#                 a = pixdata[x, y]
#                 pixdata[x, y] =  a[:-1] + (a[-1]-74,)
#
#     # Save as PNG
#     black.save(output_file, "png")

def delete_temp_files(the_directory):
    time_minus_30_min = datetime.now() - timedelta(minutes=30)

    for temp_folder in os.listdir(the_directory):
        temp_folder_path = os.path.join(the_directory, temp_folder)
        directory_time = datetime.fromtimestamp(os.path.getmtime(temp_folder_path))
        if directory_time < time_minus_30_min:
            try:
                shutil.rmtree(temp_folder_path)
            except:
                pass


@app.route('/getdem')
def getDem():
    # delete old stuff
    thread.start_new_thread(delete_temp_files, (tempZipDir))

    has_error = False
    out_srid = request.args.get('outsrid', '4326')
    in_srid = request.args.get('insrid', '4326')
    geom_wkt = request.args.get('geom', '')
    out_format = request.args.get('outformat', 'imagepng')

    if geom_wkt == '':
        return render_template('getDem.html', title='Get Data')

    try:
        out_srid = long(out_srid)
        in_srid = long(in_srid)
    except ValueError:
        has_error = True

    if geom_wkt == '':
        has_error = True

    if has_error:
        return 'error: check inputs'

    is_geom_valid = True

    if not in_srid == 4326:
        return 'only SRID 4326 is currently supported'

    conn = psycopg2.connect(ConnStringDEM_DB)
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

    # Create output directories and image paths
    unique_temp_directory = os.path.join(tempZipDir, str(uuid.uuid1()))
    os.makedirs(unique_temp_directory)
    temp_folder = os.path.join(unique_temp_directory, 'demDownload')
    os.makedirs(temp_folder)

    dem_tif_path = os.path.join(temp_folder, 'dem_raw_resolution.tif')
    dem_tif_resample_path = os.path.join(temp_folder, 'dem_resample.tif')
    hillshade_png_path = os.path.join(temp_folder, 'hillshade.png')
    color_gradient_png_path = os.path.join(temp_folder, 'color_gradient.png')
    color_gradient_txt_path = os.path.join(basedir, 'color.txt')

    dem_dataset = gdal.GetDriverByName('GTiff').Create(dem_tif_path, cols, rows, 1, gdalconst.GDT_Float32)

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

    warp_process_args = 'gdalwarp \
                -dstnodata 0 \
                -tr 10 10 \
                -r cubicspline \
                -overwrite \
                -multi \
                -wm 1000 \
                -co "TILED=YES" \
                {0} {1}'.format(dem_tif_path, dem_tif_resample_path)

    # run warp/resampling process
    warp_process = Popen(warp_process_args, shell=True)
    warp_process.wait()

    # Make the color gradient
    color_gradient_process_args = 'gdaldem color-relief -of PNG -alpha {0} {1} {2}'.\
        format(dem_tif_resample_path, color_gradient_txt_path, color_gradient_png_path)

    color_gradient_process = Popen(color_gradient_process_args, shell=True)

    # make the hillshade
    hillshade_process_args = 'gdaldem hillshade {0} {1} -of PNG -z 2'.format(dem_tif_resample_path, hillshade_png_path)

    hillshade_process = Popen(hillshade_process_args, shell=True)

    hillshade_process.wait()

    # Be sure the color gradient process has finished
    color_gradient_process.wait()

    # default case, return the png image to the client
    if out_format == 'imagepng':
        return send_file(color_gradient_png_path, mimetype='image/png')

    # if out_format is base64png, return the base64 representation of the raster
    elif out_format == 'base64png':
        with open(color_gradient_png_path, 'rb') as img:
            color_gradient_base64 = base64.b64encode(img.read())
        with open(hillshade_png_path, 'rb') as img:
            transparent_hillshade_base64 = base64.b64encode(img.read())
        response_string = '"color_gradient_base64": "{0}",\
                     "transparent_hillshade_base64": "{1}"'.format(color_gradient_base64, transparent_hillshade_base64)
        return '{' + response_string + '}'

    # if the format is zip, return the zip file
    elif out_format == 'zip':
        zip_file_out = temp_folder
        shutil.make_archive(zip_file_out, format="zip", root_dir=temp_folder)
        zip_file_out += '.zip'
        return send_file(zip_file_out, mimetype='application/zip', as_attachment='demDownload.zip')

    else:
        return "url parameter error"
