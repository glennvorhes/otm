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
    hasError = False
    outSrid = request.args.get('outsrid', '4326')
    inSrid = request.args.get('insrid', '4326')
    geomWKT = request.args.get('geom', '')
    outFormat = request.args.get('outformat', 'imagepng')

    if geomWKT == '':
        return render_template('getDem.html', title='Get Data')

    try:
        outSrid = long(outSrid)
        inSrid = long(inSrid)
    except:
        hasError = True

    if geomWKT == '':
        hasError = True

    if hasError:
        return 'error: check inputs'

    isGeomValid = True

    if not inSrid == 4326:
        return 'only SRID 4326 is currently supported'

    conn = psycopg2.connect(ConnStringDEM_DB)
    cur = conn.cursor()

    try:
        cur.execute("select ST_IsValid(ST_GeomFromText('{0}',{1})) as isvalid, \
                    ST_Area(ST_Transform(ST_GeomFromText('{0}',{1}),3857)) as area".format(geomWKT, inSrid))
        result = cur.fetchone()
        isGeomValid = bool(result[0])
        area = float(result[1])
    except:
        conn.close()
        del conn, cur
        isGeomValid = False

    # Bail out if the geometry isn't valid
    if not isGeomValid:
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
        WHERE ST_Intersects(rast, ST_GeomFromText('{0}', {1}));".format(geomWKT, inSrid, outSrid)

    cur.execute(query)
    buffer = cur.fetchone()[0]
    conn.close()

    # if outFormat is  base64png is true, return the base64 representation of the raster
    if outFormat == 'base64png':
        return base64.b64encode(buffer)
    elif outFormat == 'zip':
        # if not outSrid == 4326:
        #     return 'only implemented for output srid 4326'

        uniqueTempDirectory = os.path.join(tempZipDir, str(uuid.uuid1()))
        os.makedirs(uniqueTempDirectory)
        tempFolder = os.path.join(uniqueTempDirectory, 'demDownload')
        os.makedirs(tempFolder)

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
            WHERE ST_Intersects(rast, ST_GeomFromText('{0}', {1}));".format(geomWKT, inSrid, outSrid)

        cur.execute(query)
        metaString = cur.fetchone()[0]

        metaString = metaString.replace('(', '').replace(')', '')
        metaList = metaString.split(',')

        query = 'select srtext from spatial_ref_sys where auth_srid = {0}'.format(metaList[8])
        cur.execute(query)
        projString = cur.fetchone()[0]
        conn.close()

        aux_xml = '<PAMDataset><SRS>{0}</SRS>\
<GeoTransform>{1:E},  {2:E},  {3:E},  {4:E},  {5:E}, {6:E}</GeoTransform>\
<Metadata domain="IMAGE_STRUCTURE"><MDI key="INTERLEAVE">PIXEL</MDI></Metadata>\
</PAMDataset>'.format(projString, float(metaList[0]), float(metaList[4]), float(metaList[6]),
                      float(metaList[1]), float(metaList[7]), float(metaList[5]))

        with io.open(os.path.join(tempFolder, 'dem.png'), 'wb') as file:
            file.write(str(buffer))

        with io.open(os.path.join(tempFolder, 'dem.png.aux.xml'), 'wb') as file:
            file.write(str(aux_xml))


        zipFileOut = os.path.join(uniqueTempDirectory, 'demDownload')
        shutil.make_archive(zipFileOut, format="zip", root_dir=tempFolder)
        zipFileOut += '.zip'

        # return send_from_directory(zipFileOut, "demDownload.zip")
        return send_file(zipFileOut, mimetype='application/zip', as_attachment='demDownload.zip')


        # zipFilePath = os.path.join(uniqueTempDirectory, 'demDownload.zip')
        # zip = zipfile.ZipFile(zipFilePath, 'w', zipfile.ZIP_DEFLATED)
        # for file in os.listdir(tempFolder):
        #     zip.write(os.path.join(tempFolder, file))
        # zip.close()

        # return aux_xml
        # return 'not yet implemented'
    else:
        response = make_response(str(buffer))
        response.headers['Content-Type'] = 'image/png'
        return response
