from flask import render_template, request, make_response, send_file
from app import app, tempZipDir
import psycopg2
from config import ConnStringDEM_DB
import base64
import os
import uuid
# import io
import shutil
from osgeo import gdal, gdalconst
from subprocess import Popen
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

@app.route('/getdem')
def getDem():
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

    print query
    cur.execute(query)
    img_buffer = cur.fetchone()[0]
    print type(img_buffer)
    conn.close()

    # return str(img_buffer)

    gdal.FileFromMemBuffer('/vsimem/pnginmem', str(img_buffer))
    # print 'here1'

    # Open the in-memory file
    database_out_png_dataset = gdal.Open('/vsimem/pnginmem')

    if database_out_png_dataset is None:
        print 'Could not open '
        return 'Could not open'
    else:
        print 'opened'

    cols = database_out_png_dataset.RasterXSize
    rows = database_out_png_dataset.RasterYSize
    num_bands = database_out_png_dataset.RasterCount

    input_dataset_geotrans = database_out_png_dataset.GetGeoTransform()

    print input_dataset_geotrans[0] # top left x */
    print input_dataset_geotrans[1] #/* w-e pixel resolution */
    print input_dataset_geotrans[2] #/* 0 */
    print input_dataset_geotrans[3] #/* top left y */
    print input_dataset_geotrans[4] #/* 0 */
    print input_dataset_geotrans[5] #/* n-s pixel resolution (negative value) */


    # -te xmin ymin xmax ymax:
    te_string = '-te \
                    {0} \
                    {1} \
                    {2} \
                    {3}'\
        .format(
        input_dataset_geotrans[0],
        input_dataset_geotrans[3] + input_dataset_geotrans[5] * rows,
        input_dataset_geotrans[0] + input_dataset_geotrans[1] * cols,
        input_dataset_geotrans[3])

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
    hillshade_transparent_png_path = os.path.join(temp_folder, 'hillshade_transparent.png')
    color_gradient_png_path = os.path.join(temp_folder, 'color_gradient.png')
    color_gradient_txt_path = os.path.join(tempZipDir, 'color.txt')

    # gdal.GetDriverByName('GTiff').CreateCopy(os.path.join(temp_folder, 'dem.tif'), in_dataset)
    #
    # zip_file_out = os.path.join(unique_temp_directory, 'demDownload')
    # shutil.make_archive(zip_file_out, format="zip", root_dir=temp_folder)
    # zip_file_out += '.zip'

    dem_dataset = gdal.GetDriverByName('GTiff').Create(dem_tif_path, cols, rows, 1, gdalconst.GDT_Float32)

    # green numpy array as float
    data_float = data_grn.astype(float)

    # Add values from red and blue bands with appropriate conversion
    data_float += data_red * 256.0 + data_blu / 256.0

    out_band1 = dem_dataset.GetRasterBand(1)
    out_band1.WriteArray(data_float, 0, 0)
    out_band1.SetNoDataValue(0)
    out_band1.FlushCache()
    out_band1.GetStatistics(0, 1)

    # gdal.GetDriverByName('GTiff').CreateCopy('/home/glenn/Desktop/dem2.tif'), out_dataset))
    # dst_ds = gdal.GetDriverByName('GTiff').CreateCopy('/home/glenn/Desktop/out12.tif', out_dataset)

    dem_dataset.SetGeoTransform(input_dataset_geotrans)
    dem_dataset.SetProjection(database_out_png_dataset.GetProjection())

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

    warp_process = Popen(warp_process_args, shell=True)
    warp_process.wait()

    # Make the color gradient
    color_gradient_process_args = 'gdaldem color-relief -of PNG -alpha {0} {1} {2}'.\
        format(dem_tif_resample_path, color_gradient_txt_path, color_gradient_png_path)

    color_gradient_process = Popen(color_gradient_process_args, shell=True)

    hillshade_process_args = 'gdaldem hillshade {0} {1} -of PNG -z 2 -co "TFW=YES"'.format(dem_tif_resample_path, hillshade_png_path)

    hillshade_process = Popen(hillshade_process_args, shell=True)

    hillshade_process.wait()

    # make_transparent_hillshade(hillshade_png_path, hillshade_transparent_png_path)

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

    elif out_format == 'zip':
        zip_file_out = temp_folder
        shutil.make_archive(zip_file_out, format="zip", root_dir=temp_folder)
        zip_file_out += '.zip'

        # return send_from_directory(zip_file_out, "demDownload.zip")
        return send_file(zip_file_out, mimetype='application/zip', as_attachment='demDownload.zip')

    else:
        return "url parameter error"



#     # from flask import render_template, request, make_response, send_file
# # from app import app, tempZipDir
# import psycopg2
# from config import ConnStringDEM_DB
# import base64
# import os
# import uuid
# import io
# import shutil
# from osgeo import gdal, gdalconst
# import subprocess

#
# @app.route('/getdem') if __name__ == '__main__'
# def getDem():
#     has_error = False
#     out_srid = '3857'
#     in_srid = '4326'
#     geom_wkt = 'POLYGON((-71.02308 19.037060,-71.01501 19.017667,-70.97570 19.015314,\
#         -70.99355 19.037953,-71.02308 19.037060)) '
#     out_format = 'imagepng'
#
#     print out_srid
#
#     # if geom_wkt == '':
#     #     return render_template('getDem.html', title='Get Data')
#
#     try:
#         out_srid = long(out_srid)
#         in_srid = long(in_srid)
#     except ValueError:
#         has_error = True
#
#     if geom_wkt == '':
#         has_error = True
#
#     if has_error:
#         return 'error: check inputs'
#
#     is_geom_valid = True
#
#     if not in_srid == 4326:
#         return 'only SRID 4326 is currently supported'
#
#     conn = psycopg2.connect(ConnStringDEM_DB)
#     cur = conn.cursor()
#
#     try:
#         cur.execute("select ST_IsValid(ST_GeomFromText('{0}',{1})) as isvalid, \
#                     ST_Area(ST_Transform(ST_GeomFromText('{0}',{1}),3857)) as area".format(geom_wkt, in_srid))
#         result = cur.fetchone()
#         is_geom_valid = bool(result[0])
#         area = float(result[1])
#     except psycopg2.Error:
#         conn.close()
#         del conn, cur
#         is_geom_valid = False
#
#     # Bail out if the geometry isn't valid
#     if not is_geom_valid:
#         return 'geom not valid'
#     if area > 246952910:
#         return 'geom too big'
#
#     query = "SELECT \
#                 ST_AsGDALRaster(\
#                     ST_Transform(\
#                         ST_Clip(\
#                             ST_Union(rast),ST_GeomFromText('{0}', {1}),\
#                         true),\
#                     {2}),\
#                 'GTiff')\
#                 FROM aster_gdem \
#                 WHERE ST_Intersects(\
#                     rast, ST_GeomFromText('{0}', {1})\
#                 );".format(geom_wkt, in_srid, out_srid)
#
#     print query
#     cur.execute(query)
#     img_buffer = cur.fetchone()[0]
#     conn.close()
#
#     gdal.FileFromMemBuffer('/vsimem/pnginmem', str(img_buffer))
#
#     # Open the in-memory file
#     in_dataset = gdal.Open('/vsimem/pnginmem')
#
#     if in_dataset is None:
#         return 'Could not open'
#
#     dataset_geotrans = in_dataset.GetGeoTransform()
#
#     print dataset_geotrans[0] # top left x */
#     print dataset_geotrans[1] #/* w-e pixel resolution */
#     print dataset_geotrans[2] #/* 0 */
#     print dataset_geotrans[3] #/* top left y */
#     print dataset_geotrans[4] #/* 0 */
#     print dataset_geotrans[5] #/* n-s pixel resolution (negative value) */
#
#     cols = in_dataset.RasterXSize
#     rows = in_dataset.RasterYSize
#     bands = in_dataset.RasterCount
#
#     # -te xmin ymin xmax ymax:
#     te_string = '-te \
#                     {0} \
#                     {1} \
#                     {2} \
#                     {3}'\
#         .format(
#         dataset_geotrans[0],
#         dataset_geotrans[3] + dataset_geotrans[5] * rows,
#         dataset_geotrans[0] + dataset_geotrans[1] * cols,
#         dataset_geotrans[3]
#     )
#
#     print te_string
#
#
#     data_red = in_dataset.GetRasterBand(1).ReadAsArray(0, 0, cols, rows)
#     data_grn = in_dataset.GetRasterBand(2).ReadAsArray(0, 0, cols, rows)
#     data_blu = in_dataset.GetRasterBand(3).ReadAsArray(0, 0, cols, rows)
#
#     out_dataset = gdal.GetDriverByName('MEM').Create('inMem', cols, rows, 1, gdalconst.GDT_Float32)
#
#     # print type(out_dataset)
#
#     data_float = data_grn.astype(float)
#     data_float += data_red * 256.0 + data_blu / 256.0
#
#     out_band1 = out_dataset.GetRasterBand(1)
#     out_band1.WriteArray(data_float, 0, 0)
#     out_band1.SetNoDataValue(0)
#     out_band1.FlushCache()
#     out_band1.GetStatistics(0, 1)
#
#     out_dataset.SetGeoTransform(dataset_geotrans)
#     out_dataset.SetProjection(in_dataset.GetProjection())
#
#     gdal.GetDriverByName('GTiff').CreateCopy('out21.tif', out_dataset)
#
#     in_dataset = None
#     dst_ds = None
#     out_dataset = None
#     out_band1 = None
#
#
#
#     processArgs = ['gdalwarp',
#                    '-dstnodata 0',
#                    '-tr 1 1',
#                    '-r cubicspline',
#                    '-multi',
#                    '-co "TILED=YES"',
#                    '-overwrite',
#                    '-wm 1000',
#                    '~/PycharmProjects/testing/out21.tif',
#                    '~/PycharmProjects/testing/outwarp4.tif']
#
#     processArgs = ['gdalwarp',
#                    # '-dstnodata 0',
#                    # '-tr 1 1',
#                    # '-r cubicspline',
#                    '-t_srs EPSG:3857',
#                    # '-multi',
#                    # '-co "TILED=YES"',
#                    '-overwrite',
#                    # '-wm 1000',
#                    'out21.tif',
#                    'outwarp4.tif']
#
#
#     # gdalwarp -dstnodata 0 -tr 10 10 -r cubicspline -multi -co "TILED=YES" out20.tif outwarp3.tif
#
#     processArgs = 'gdalwarp -dstnodata 0 -tr 10 10 -r cubicspline -multi -co "TILED=YES" out21.tif outwarp3.tif'
#
#     processArgs = 'gdalwarp -dstnodata 0 -tr 10 10 -r cubicspline -overwrite -t_srs EPSG:3857 -multi -wm 1000 -co "TILED=YES" out21.tif outwarp3.tif'
#     processArgs = 'gdalwarp \
#                     -dstnodata 0 \
#                     -tr 10 10 \
#                     -r cubicspline \
#                     -overwrite \
#                     -multi \
#                     -wm 1000 \
#                     -co "TILED=YES" \
#                     {0} \
#                     out21.tif \
#                     outwarp3.tif'.format(te_string)
#
#
#     proc = subprocess.Popen(processArgs, shell=True)
#     proc.wait()
#
#     processArgs = 'gdaldem hillshade outwarp3.tif ouths.tif -z 2 -co "TFW=YES"'
#
#     proc = subprocess.Popen(processArgs, shell=True)
#     proc.wait()
#
#
#     processArgs = 'gdaldem color-relief -of PNG outwarp3.tif color.txt output_color1.png'
#     proc = subprocess.Popen(processArgs, shell=True)
#     proc.wait()
#
#
#
#
#          #
#
#     # b1 = np.floor(dataFloat / 256.0).astype(int)
#     # b2 = np.floor(dataFloat % 256.0).astype(int)
#     # b3 = np.round((dataFloat % 1) * 256.0).astype(int)
#
#
#
#
#     # band = in_dataset.GetRasterBand(1)
#     #
#     # data = band.ReadAsArray(0, 0, cols, rows)
#     #
#     # dataFloat = data.astype(float)
#
#     # b1 = np.floor(dataFloat / 256.0).astype(int)
#     # b2 = np.floor(dataFloat % 256.0).astype(int)
#     # b3 = np.round((dataFloat % 1) * 256.0).astype(int)
#     #
#     # # Adjust case where b3 rounds to 256
#     # adjustB3 = (b3 > 255).astype(int)
#     # b3 -= adjustB3
#     # b2 += adjustB3
#     #
#     # # Need to check b2 as well now
#     # adjustB2 = (b2 > 255).astype(int)
#     # b2 -= adjustB2
#     # b1 += adjustB2
#     #
#     # outDataset = gdal.GetDriverByName('MEM').Create('inMem', cols, rows, 3, gdalconst.GDT_Byte)
#     #
#     # outDataset.SetGeoTransform(inDataset.GetGeoTransform())
#     # outDataset.SetProjection(inDataset.GetProjection())
#     #
#     # outBand1 = outDataset.GetRasterBand(1)
#     # outBand1.WriteArray(b1, 0, 0)
#     # outBand2 = outDataset.GetRasterBand(2)
#     # outBand2.WriteArray(b2, 0, 0)
#     # outBand3 = outDataset.GetRasterBand(3)
#     # outBand3.WriteArray(b3, 0, 0)
#     #
#     # gdal.GetDriverByName('PNG').CreateCopy(outputFile, outDataset)
#     #
#     # inDataset = None
#     # outDataset = None
#
#     # gdal.GetDriverByName('GTiff').CreateCopy('/home/glenn/Desktop/out.tif', in_dataset)
#
#     print 'hatter4'
#     return
#
#     # default case, return the png image to the client
#     if out_format == 'imagepng':
#         response = make_response(str(img_buffer))
#         response.headers['Content-Type'] = 'image/png'
#         return response
#
#     # if out_format is base64png, return the base64 representation of the raster
#     elif out_format == 'base64png':
#         return base64.b64encode(img_buffer)
#
#     elif out_format == 'zip':
#         # if not out_srid == 4326:
#         #     return 'only implemented for output srid 4326'
#
#         unique_temp_directory = os.path.join(tempZipDir, str(uuid.uuid1()))
#         os.makedirs(unique_temp_directory)
#         temp_folder = os.path.join(unique_temp_directory, 'demDownload')
#         os.makedirs(temp_folder)
#
#         gdal.GetDriverByName('GTiff').CreateCopy(os.path.join(temp_folder, 'dem.tif'), in_dataset)
#
#         zip_file_out = os.path.join(unique_temp_directory, 'demDownload')
#         shutil.make_archive(zip_file_out, format="zip", root_dir=temp_folder)
#         zip_file_out += '.zip'
#
#         # return send_from_directory(zip_file_out, "demDownload.zip")
#         return send_file(zip_file_out, mimetype='application/zip', as_attachment='demDownload.zip')
#
#     else:
#         return "url parameter error"
#
#
#
# if __name__ == '__main__':
#     getDem()
#     print 'here'


