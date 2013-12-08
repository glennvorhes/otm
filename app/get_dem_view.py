from flask import render_template, request, make_response, send_file
from app import app, tempZipDir
import psycopg2
from config import ConnStringDEM_DB
import base64
import os
import uuid
import io
import shutil

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
        ST_AsPNG(\
            ST_Transform(\
                ST_Clip(\
                    ST_Union(rast),ST_GeomFromText('{0}', {1}), true)\
                ,{2})\
            )\
        FROM aster_gdem \
        WHERE ST_Intersects(rast, ST_GeomFromText('{0}', {1}));".format(geom_wkt, in_srid, out_srid)

    cur.execute(query)
    img_buffer = cur.fetchone()[0]
    print type(img_buffer)
    conn.close()

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

        conn = psycopg2.connect(ConnStringDEM_DB)
        cur = conn.cursor()

        query = "SELECT \
            ST_MetaData(\
                ST_Transform(\
                    ST_Clip(\
                        ST_Union(rast),ST_GeomFromText('{0}', {1}), true)\
                    ,{2})\
                )\
            FROM aster_gdem \
            WHERE ST_Intersects(rast, ST_GeomFromText('{0}', {1}));".format(geom_wkt, in_srid, out_srid)

        cur.execute(query)
        meta_string = cur.fetchone()[0]

        meta_string = meta_string.replace('(', '').replace(')', '')
        meta_list = meta_string.split(',')

        query = 'select srtext from spatial_ref_sys where auth_srid = {0}'.format(meta_list[8])
        cur.execute(query)
        proj_string = cur.fetchone()[0]
        conn.close()

        aux_xml = '<PAMDataset><SRS>{0}</SRS>\
<GeoTransform>{1:E},  {2:E},  {3:E},  {4:E},  {5:E}, {6:E}</GeoTransform>\
<Metadata domain="IMAGE_STRUCTURE"><MDI key="INTERLEAVE">PIXEL</MDI></Metadata>\
</PAMDataset>'.format(proj_string, float(meta_list[0]), float(meta_list[4]), float(meta_list[6]),
                      float(meta_list[1]), float(meta_list[7]), float(meta_list[5]))

        with io.open(os.path.join(temp_folder, 'dem.png'), 'wb') as img_file:
            img_file.write(str(img_buffer))

        with io.open(os.path.join(temp_folder, 'dem.png.aux.xml'), 'wb') as aux_file:
            aux_file.write(str(aux_xml))

        zip_file_out = os.path.join(unique_temp_directory, 'demDownload')
        shutil.make_archive(zip_file_out, format="zip", root_dir=temp_folder)
        zip_file_out += '.zip'

        # return send_from_directory(zip_file_out, "demDownload.zip")
        return send_file(zip_file_out, mimetype='application/zip', as_attachment='demDownload.zip')

        # zipFilePath = os.path.join(unique_temp_directory, 'demDownload.zip')
        # zip = zipfile.ZipFile(zipFilePath, 'w', zipfile.ZIP_DEFLATED)
        # for file in os.listdir(temp_folder):
        #     zip.write(os.path.join(temp_folder, file))
        # zip.close()

        # return aux_xml
        # return 'not yet implemented'
        # if out_format is  base64png is true, return the base64 representation of the raster

    else:
        return "url parameter error"

