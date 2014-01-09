from flask import render_template, request, send_file
from app import app
from config import ConnStringDEM_DB
from gen_design.gdal_operations import GdalOperations, GDAL_OPERATIONS_PROPS
import base64
import os
import shutil
from datetime import datetime, timedelta
from config import tempZipDir
import thread


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
    thread.start_new_thread(delete_temp_files, (tempZipDir,))

    has_error = False
    out_srid = request.args.get('outsrid', '4326')
    in_srid = request.args.get('insrid', '4326')
    geom_wkt = request.args.get('geom', '')
    out_format = request.args.get('outformat', 'imagepng')

    if geom_wkt == '':
        return render_template('getDem.html', title='Get Data')

    geom_check = geom_wkt
    assert(isinstance(geom_check, str))

    geom_check.replace('POLYGON((', '').replace('))', '')

    if len(geom_check.split(',')) < 3:
        has_error = True

    try:
        out_srid = long(out_srid)
        in_srid = long(in_srid)
    except ValueError:
        has_error = True

    if geom_wkt == '':
        has_error = True

    if has_error:
        return 'error: check inputs'

    gdal_ops = GdalOperations(tempZipDir, ConnStringDEM_DB)
    gdal_ops.image_from_database(geom_wkt, in_srid, out_srid)

    # default case, return the png image to the client
    if out_format == 'imagepng':
        color_gradient_png_path = gdal_ops.get_file_path(GDAL_OPERATIONS_PROPS.COLOR_GRADIENT)
        return send_file(color_gradient_png_path, mimetype='image/png')

    # if out_format is base64png, return the base64 representation of the raster
    elif out_format == 'base64png':
        color_gradient_png_path = gdal_ops.get_file_path(GDAL_OPERATIONS_PROPS.COLOR_GRADIENT)
        with open(color_gradient_png_path, 'rb') as img:
            color_gradient_base64 = base64.b64encode(img.read())
        hillshade_png_path = gdal_ops.get_file_path(GDAL_OPERATIONS_PROPS.HILLSHADE)
        with open(hillshade_png_path, 'rb') as img:
            hillshade_base64 = base64.b64encode(img.read())
        response_string = '"color_gradient_base64": "{0}",\
                     "hillshade_base64": "{1}"'.format(color_gradient_base64, hillshade_base64)
        return '{' + response_string + '}'

    # if the format is zip, return the zip file
    elif out_format == 'zip':
        gdal_ops.make_image_warp()
        gdal_ops.make_hillshade()
        gdal_ops.make_color_gradient()
        gdal_ops.make_slope()
        gdal_ops.make_aspect()
        zip_file_out = gdal_ops.get_file_path(GDAL_OPERATIONS_PROPS.ZIP_FILE)
        return send_file(zip_file_out, mimetype='application/zip', as_attachment='demDownload.zip')

    else:
        return "url parameter error"
