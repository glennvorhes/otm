__author__ = 'glenn'
from flask import render_template, session, request, jsonify
from app import app, DatabaseSessionMaker
from geoalchemy2.elements import WKTElement
from datetime import datetime
import simplejson
from sqlalchemy import func
import exampleFeatures


@app.route('/example/terrainmap')
def terrainMap():
    return render_template('terrainMap.html', title='Terrain Map')


@app.route('/example/infrastructure')
def infraExample():
    if 'currentProject' in session.keys():
        del session['currentProject']
     # It doesn't like to put the geom in the session
    # Just make a dictionary with a geojson string,
    # Saves us having to get the features later
    props = {}
    props['pid'] = -1
    props['uid'] = -1
    props['tid'] = 2
    props['project_name'] = "Example Project"
    props['created'] = datetime.now().strftime('%Y-%m-%d')
    props['last_modfied'] = datetime.now().strftime('%Y-%m-%d')
    props['description'] = "Gravity Fed Water Supply"
    props['geom'] = exampleFeatures.exampleExtent
    props['publicExample'] = True

    jsonProps = simplejson.dumps(props)
    return render_template('map.html',
                           title=props['project_name'],
                           jsonProps=jsonProps)


@app.route('/example/getfeatures')
def exampleGetFeatures():
    session['maxfid'] = 100
    return exampleFeatures.exampleFeatJSON


@app.route('/example/addfeature', methods=['POST'])
def exampleAddfeature():
    maxfid = int(session['maxfid']);
    maxfid += 1
    session['maxfid'] = maxfid

    geomWKT = str(request.form["geomWKT"])
    srid_raw = str(request.form["srid"])
    # Just need the SRID number
    srid = long(srid_raw[srid_raw.find(':')+1:])
    geomType = str(request.form["geomType"]).upper()
    currentLayer = str(request.form["currentLayer"]).upper()

    newGeom = WKTElement(geomWKT, srid=srid)
    # Check the geometry before proceeding
    # geomSimple =  db_session.scalar(func.is_simple(newGeom))ST_IsValid
    db_session = DatabaseSessionMaker()
    geomValid = db_session.scalar(func.ST_IsValid(newGeom))
    db_session.close()

    if not (geomValid):
        return jsonify(fid=-1)

    featureProperties = {}

    print currentLayer + geomType
    if currentLayer == 'DWELLING' and geomType == 'POINT':
        featureProperties = {"occupants": 3, "fid": maxfid, "owner": None}
    elif currentLayer == 'DWELLING' and geomType == 'POLYGON':
        featureProperties = {"occupants": 3, "fid": maxfid, "owner": None}
    elif currentLayer == 'IMPEDANCE' and geomType == 'LINESTRING':
        featureProperties = {"fid": maxfid, "impedance": None}
    elif currentLayer == 'IMPEDANCE' and geomType == 'POLYGON':
        featureProperties = {"fid": maxfid, "impedance": None}
    elif currentLayer == 'WATER'and geomType == 'POINT':
        featureProperties = {"fid": maxfid, "description": None, "flow_rate_gpm": None}
    elif currentLayer == 'TANK' and geomType == 'POLYGON':
        featureProperties = {"fid": maxfid, "description": None}
    elif currentLayer == 'TREATMENT' and geomType == 'POLYGON':
        featureProperties = {"fid": maxfid, "description": None}
    else:
        return jsonify(fid=-2)

    return jsonify(fid=featureProperties['fid'], featureProperties=featureProperties)


@app.route('/example/editfeaturegeom', methods=['POST'])
def exampleEditFeatures():
    geomWKT = str(request.form["geomWKT"])
    # Just need the SRID number
    srid_raw = str(request.form["srid"])
    srid = long(srid_raw[srid_raw.find(':')+1:])
    featFID = long(request.form["fid"])

    newGeom = WKTElement(geomWKT, srid=srid)
    # Check the geometry before proceeding
    db_session = DatabaseSessionMaker()
    geomValid = db_session.scalar(func.ST_IsValid(newGeom))
    db_session.close()
    # geomSimple = db_session.scalar(func.is_simple(newGeom))
    # geomValid = db_session.scalar(func.is_valid(newGeom))
    if not geomValid:
        return jsonify(fid=-1)
    else:
        return jsonify(fid=featFID)


@app.route('/example/updateextent', methods=['POST'])
def exampleUpdateExtent():
    print 'Heerrrererer'
    # Task ids add: 1, modify:2, clear:3
    update_task = int(request.form["updatetask"])
    if update_task == 1 or update_task == 2:

        geom_wkt = str(request.form["geomWKT"])
        srid_raw = str(request.form["srid"])
        # Just need the SRID number
        srid = long(srid_raw[srid_raw.find(':')+1:])

        geom_check = geom_wkt
        geom_check.replace('POLYGON((', '').replace('))', '')

        if len(geom_check.split(',')) > 3:
            db_session = DatabaseSessionMaker()
            new_geom = WKTElement(geom_wkt, srid=srid)
            # Check the geometry before proceeding
            geom_valid = db_session.scalar(func.ST_IsValid(new_geom))
            db_session.close()
        else:
            geom_valid = False

        if geom_valid:
            return jsonify(code=1)
        else:
            return jsonify(code=-1)

    elif update_task == 3:
        return jsonify(code=1)
    else:
        return jsonify(code=-2)

