from flask import render_template, request, make_response, send_file
from app import app, tempZipDir
import psycopg2
from config import ConnStringDEM_DB
import base64
import os
import uuid
import io
import shutil
from osgeo import gdal, gdalconst


@app.route('/getdem')
def getDem():
    has_error = False
    out_srid = request.args.get('out_srid', '4326')
    in_srid = request.args.get('in_srid', '4326')
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
    in_dataset = gdal.Open('/vsimem/pnginmem')

    if in_dataset is None:
        print 'Could not open '
        # sys.exit(1)
    else:
        print 'opened'

    cols = in_dataset.RasterXSize
    rows = in_dataset.RasterYSize
    bands = in_dataset.RasterCount

    data_red = in_dataset.GetRasterBand(1).ReadAsArray(0, 0, cols, rows)
    data_grn = in_dataset.GetRasterBand(2).ReadAsArray(0, 0, cols, rows)
    data_blu = in_dataset.GetRasterBand(3).ReadAsArray(0, 0, cols, rows)

    # out_dataset = gdal.GetDriverByName('MEM').Create('inMem', cols, rows, 1, gdalconst.GDT_Byte)
    f_name = '/home/glenn/Desktop/out16.tif'

    out_dataset = gdal.GetDriverByName('GTiff').Create(f_name, cols, rows, 1, gdalconst.GDT_Float32)

    data_float = data_grn.astype(float)
    data_float += data_red * 256.0 + data_blu / 256.0
    # print data_float[]

    # data_grn *= 5
    # data_grn = data_grn.astype(float)
    #

    out_band1 = out_dataset.GetRasterBand(1)
    out_band1.WriteArray(data_float, 0, 0)
    out_band1.SetNoDataValue(0)
    out_band1.FlushCache()
    out_band1.GetStatistics(0, 1)

    # gdal.GetDriverByName('GTiff').CreateCopy('/home/glenn/Desktop/dem2.tif'), out_dataset))
    # dst_ds = gdal.GetDriverByName('GTiff').CreateCopy('/home/glenn/Desktop/out12.tif', out_dataset)

    out_dataset.SetGeoTransform(in_dataset.GetGeoTransform())
    out_dataset.SetProjection(in_dataset.GetProjection())

    in_dataset = None
    dst_ds = None
    out_dataset = None
    out_band1 = None
         #

    # b1 = np.floor(dataFloat / 256.0).astype(int)
    # b2 = np.floor(dataFloat % 256.0).astype(int)
    # b3 = np.round((dataFloat % 1) * 256.0).astype(int)




    # band = in_dataset.GetRasterBand(1)
    #
    # data = band.ReadAsArray(0, 0, cols, rows)
    #
    # dataFloat = data.astype(float)

    # b1 = np.floor(dataFloat / 256.0).astype(int)
    # b2 = np.floor(dataFloat % 256.0).astype(int)
    # b3 = np.round((dataFloat % 1) * 256.0).astype(int)
    #
    # # Adjust case where b3 rounds to 256
    # adjustB3 = (b3 > 255).astype(int)
    # b3 -= adjustB3
    # b2 += adjustB3
    #
    # # Need to check b2 as well now
    # adjustB2 = (b2 > 255).astype(int)
    # b2 -= adjustB2
    # b1 += adjustB2
    #
    # outDataset = gdal.GetDriverByName('MEM').Create('inMem', cols, rows, 3, gdalconst.GDT_Byte)
    #
    # outDataset.SetGeoTransform(inDataset.GetGeoTransform())
    # outDataset.SetProjection(inDataset.GetProjection())
    #
    # outBand1 = outDataset.GetRasterBand(1)
    # outBand1.WriteArray(b1, 0, 0)
    # outBand2 = outDataset.GetRasterBand(2)
    # outBand2.WriteArray(b2, 0, 0)
    # outBand3 = outDataset.GetRasterBand(3)
    # outBand3.WriteArray(b3, 0, 0)
    #
    # gdal.GetDriverByName('PNG').CreateCopy(outputFile, outDataset)
    #
    # inDataset = None
    # outDataset = None

    # gdal.GetDriverByName('GTiff').CreateCopy('/home/glenn/Desktop/out.tif', in_dataset)

    # return 'hatter1'








    # default case, return the png image to the client
    if out_format == 'imagepng':
        response = make_response(str(img_buffer))
        response.headers['Content-Type'] = 'image/png'
        return response

    # if out_format is base64png, return the base64 representation of the raster
    elif out_format == 'base64png':
        return base64.b64encode(img_buffer)

    elif out_format == 'zip':
        # if not out_srid == 4326:
        #     return 'only implemented for output srid 4326'

        unique_temp_directory = os.path.join(tempZipDir, str(uuid.uuid1()))
        os.makedirs(unique_temp_directory)
        temp_folder = os.path.join(unique_temp_directory, 'demDownload')
        os.makedirs(temp_folder)

        gdal.GetDriverByName('GTiff').CreateCopy(os.path.join(temp_folder, 'dem.tif'), in_dataset)

        zip_file_out = os.path.join(unique_temp_directory, 'demDownload')
        shutil.make_archive(zip_file_out, format="zip", root_dir=temp_folder)
        zip_file_out += '.zip'

        # return send_from_directory(zip_file_out, "demDownload.zip")
        return send_file(zip_file_out, mimetype='application/zip', as_attachment='demDownload.zip')

    else:
        return "url parameter error"

