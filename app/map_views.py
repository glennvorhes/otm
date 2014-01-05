from flask import render_template, redirect, session, url_for, request, jsonify
from flask_login import login_required
from app import app, models, DatabaseSessionMaker
from geoalchemy2.elements import WKTElement
from datetime import datetime
import simplejson
# from sqlalchemy import func
from geoalchemy2 import functions as geoalchemy_func


@app.route('/map/getfeatures')
@login_required
def getfeatures():
    db_session = DatabaseSessionMaker()
    jsonstring = '{ "type": "FeatureCollection",\n\t"features": [\n'
    try:
        currentProjectPID = int(session['currentProject']['pid'])
    except:
        jsonstring += '\t]\n}'
        return jsonstring

    currentProject = db_session.query(models.Project).get(currentProjectPID)
    feats = currentProject.features
    hasFeats = False
    for f in feats:
        hasFeats = True
        jsonstring += '\t\t{\n\t\t"type": "Feature"'
        jsonstring += ',\n\t\t"geometry": ' + db_session.scalar(geoalchemy_func.ST_AsGeoJSON(f.geom))
        jsonstring += ',\n' + f.getGeoJSONProps()
        jsonstring += '\n\t\t},\n'
    if hasFeats:
        jsonstring = jsonstring[:jsonstring.rfind(',')] + '\n'

    jsonstring += '\t]\n}'
    db_session.close()
    return jsonstring


@app.route('/map', methods=['GET', 'POST'])
@login_required
def showmap():
    db_session = DatabaseSessionMaker()
    #if a project has not been selected in the projects page, return there
    if not 'currentpid' in session:
        return redirect(url_for('getProjects'))

    getpid = long(session['currentpid'])

    thisproj = db_session.query(models.Project).get(getpid)
    thisproj.last_modified = datetime.now()
    db_session.commit()
    thistype = db_session.query(models.Project_Type).get(thisproj.tid)

    # It doesn't like to put the geom in the session
    # Just make a dictionary with a geojson string,
    # Saves us having to get the features later
    props = {'pid': thisproj.pid,
             'uid': thisproj.uid,
             'tid': thistype.tid,
             'project_name': thisproj.project_name,
             'created': thisproj.created.strftime('%Y-%m-%d'),
             'last_modfied': thisproj.last_modified.strftime('%Y-%m-%d'),
             'description': thistype.description
             }

    if thisproj.geom is None:
        props['geom'] = None
    else:
        props['geom'] = db_session.scalar(geoalchemy_func.ST_AsGeoJSON(thisproj.geom))
        print props['geom']

    session['currentProject'] = props

    jsonProps = simplejson.dumps(session['currentProject'])
    db_session.close()
    return render_template('map.html',
                           title=session['currentProject']['project_name'],
                           jsonProps=jsonProps)


@app.route('/map/addfeature', methods=['POST'])
@login_required
def addfeature():
    db_session = DatabaseSessionMaker()
    geomWKT = str(request.form["geomWKT"])
    srid_raw = str(request.form["srid"])
    # Just need the SRID number
    srid = long(srid_raw[srid_raw.find(':')+1:])
    geomType = str(request.form["geomType"]).upper()
    currentLayer = str(request.form["currentLayer"]).upper()

    newGeom = WKTElement(geomWKT, srid=srid)
    # Check the geometry before proceeding
    geomValid = db_session.scalar(geoalchemy_func.ST_IsValid(newGeom))
    if not geomValid:
        db_session.close()
        return jsonify(fid=-1, valid=False)



    proj = db_session.query(models.Project).get(session['currentProject']['pid'])

    print currentLayer + geomType
    if currentLayer == 'DWELLING' and geomType == 'POINT':
        newFeature = models.Dwelling_Point(prj=proj, geom=newGeom)
    elif currentLayer == 'DWELLING' and geomType == 'POLYGON':
        newFeature = models.Dwelling_Polygon(prj=proj, geom=newGeom)
    elif currentLayer == 'IMPEDANCE' and geomType == 'LINESTRING':
        newFeature = models.Impedance_LineString(prj=proj, geom=newGeom)
    elif currentLayer == 'IMPEDANCE' and geomType == 'POLYGON':
        newFeature = models.Impedance_Polygon(prj=proj, geom=newGeom)
    elif currentLayer == 'WATER'and geomType == 'POINT':
        newFeature = models.Water_Source(prj=proj, geom=newGeom)
    elif currentLayer == 'TANK' and geomType == 'POLYGON':
        newFeature = models.Tank_Site(prj=proj, geom=newGeom)
    elif currentLayer == 'TREATMENT' and geomType == 'POLYGON':
        newFeature = models.Treatment_Site(prj=proj, geom=newGeom)
    else:
        return jsonify(fid=-2)

    db_session.add(newFeature)
    db_session.commit()

    skipList = ['prj', 'metadata', 'getGeoJSONProps', 'discriminator', 'created', 'geom', 'pid']
    props = dir(newFeature)

    featureProperties = {}

    for p in props:
        if p.startswith('_') or p in skipList:
            continue
        else:
            featureProperties[p]=getattr(newFeature, p)
    db_session.close()
    return jsonify(fid=newFeature.fid, featureProperties=featureProperties)


@app.route('/map/editfeaturegeom', methods=['POST'])
@login_required
def editfeaturegeom():
    db_session = DatabaseSessionMaker()
    geomWKT = str(request.form["geomWKT"])
    # Just need the SRID number
    srid_raw = str(request.form["srid"])
    srid = long(srid_raw[srid_raw.find(':')+1:])
    featFID = long(request.form["fid"])

    newGeom = WKTElement(geomWKT, srid=srid)
    # Check the geometry before proceeding
    geomValid = db_session.scalar(geoalchemy_func.ST_IsValid(newGeom))
    # geomSimple = db_session.scalar(geoalchemy_func.is_simple(newGeom))
    # geomValid = db_session.scalar(geoalchemy_func.is_valid(newGeom))
    if not geomValid:
        return jsonify(fid=-1)
    updateFeature = db_session.query(models.Feature).get(featFID)
    updateFeature.geom = newGeom
    db_session.commit()
    db_session.close()
    return jsonify(fid=featFID)


@app.route('/map/updateextent', methods=['POST'])
@login_required
def updateextent():
    db_session = DatabaseSessionMaker()
    # Task ids add: 1, modify:2, clear:3
    updateTask = int(request.form["updatetask"])
    if updateTask == 1 or updateTask == 2:
        geomWKT = str(request.form["geomWKT"])
        srid_raw = str(request.form["srid"])
        # Just need the SRID number
        srid = long(srid_raw[srid_raw.find(':')+1:])

        newGeom = WKTElement(geomWKT, srid=srid)
        # Check the geometry before proceeding
        # geomSimple =  db_session.scalar(geoalchemy_func.is_simple(newGeom))
        # geomValid =  db_session.scalar(geoalchemy_func.is_valid(newGeom))
        geomValid = db_session.scalar(geoalchemy_func.ST_IsValid(newGeom))

        if not geomValid:
            return jsonify(code=-1)

        proj = db_session.query(models.Project).get(session['currentProject']['pid'])

        proj.geom = newGeom
        db_session.commit()
        # extentGeojson = db_session.scalar(geoalchemy_func.ST_AsGeoJSON(newGeom))
        return jsonify(code=1)

    elif updateTask == 3:
        proj = db_session.query(models.Project).get(session['currentProject']['pid'])
        proj.geom = None
        db_session.commit()
        db_session.close()
        return jsonify(code=1)
    else:
        db_session.close()
        return jsonify(code=-2)


@app.route('/map/deletefeature', methods=['POST'])
@login_required
def deletefeature():
    db_session = DatabaseSessionMaker()
    # Task ids add: 1, modify:2, clear:3
    deleteFID = int(request.form["deleteFID"])
    deleteFeature = db_session.query(models.Feature).get(deleteFID)
    db_session.delete(deleteFeature)
    db_session.commit()
    db_session.close()
    return jsonify(success=0)

