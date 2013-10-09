from flask import render_template, flash, redirect, session, url_for, request, g, jsonify, make_response, send_file, send_from_directory
from flask_login import login_user, logout_user, current_user, login_required
from app import app, db_session, lm, oid, models, tempZipDir
import forms
from geoalchemy2.elements import WKTElement
from datetime import datetime
import simplejson
from sqlalchemy import func
from bs4 import BeautifulSoup
import psycopg2
from config import ConnStringDEM_DB
import base64
import exampleFeatures
import os
import uuid
import io
import shutil





@app.route('/testurl')
def testurl():
    return 'At the test url, more stuff'

@app.route('/testtemplate')
def testtemplate():
    currentDate = datetime.now()
    userName = 'Glenn'
    alertString = 'An alert from the Server'
    return render_template('testtemplate.html',
                           theDate=currentDate,
                           theName=userName,
                           flaskAlert=alertString)

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
    geomValid = db_session.scalar(func.ST_IsValid(newGeom))
    # geomValid =  db_session.scalar(func.is_valid(newGeom))
    if not (geomValid):
        return jsonify(fid=-1)

    featureProperties = {}

    print currentLayer + geomType
    if currentLayer == 'DWELLING' and geomType == 'POINT':
        featureProperties = {"occupants":3, "fid": maxfid, "owner": None}
    elif currentLayer == 'DWELLING' and geomType == 'POLYGON':
        featureProperties = {"occupants":3, "fid": maxfid, "owner": None}
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
    geomValid = db_session.scalar(func.ST_IsValid(newGeom))
    # geomSimple = db_session.scalar(func.is_simple(newGeom))
    # geomValid = db_session.scalar(func.is_valid(newGeom))
    if not geomValid:
        return jsonify(fid=-1)
    else:
        return jsonify(fid=featFID)

@app.route('/example/updateextent', methods=['POST'])
def exampleUpdateExtent():
    # Task ids add: 1, modify:2, clear:3
    updateTask = int(request.form["updatetask"])
    if updateTask == 1 or updateTask == 2:
        geomWKT = str(request.form["geomWKT"])
        srid_raw = str(request.form["srid"])
        # Just need the SRID number
        srid = long(srid_raw[srid_raw.find(':')+1:])

        newGeom = WKTElement(geomWKT, srid=srid)
        # Check the geometry before proceeding
        # geomSimple =  db_session.scalar(func.is_simple(newGeom))
        # geomValid =  db_session.scalar(func.is_valid(newGeom))
        geomValid = db_session.scalar(func.ST_IsValid(newGeom))

        if not geomValid:
            return jsonify(code=-1)
        return jsonify(code=1)

    elif updateTask == 3:
        return jsonify(code=1)
    else:
        return jsonify(code=-2)


@app.route('/getdem')
def getDem():
    hasError = False
    outSrid = request.args.get('outsrid', '4326')
    inSrid = request.args.get('insrid', '4326')
    geomWKT = request.args.get('geom', '')
    outFormat = request.args.get('outformat', 'imagepng')

    if geomWKT == '':
        return render_template('getDem.html', title='Get Elevation Model')

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


        # print projString
        # projString = projString.replace('"', '&quot')

        # aux_xml = '''
        # <PAMDataset>
        #   <SRS>GEOGCS[&quot;WGS 84&quot;,DATUM[&quot;WGS_1984&quot;,SPHEROID[&quot;WGS 84&quot;,6378137,298.257223563,AUTHORITY[&quot;EPSG&quot;,&quot;7030&quot;]],AUTHORITY[&quot;EPSG&quot;,&quot;6326&quot;]],PRIMEM[&quot;Greenwich&quot;,0],UNIT[&quot;degree&quot;,0.0174532925199433],AUTHORITY[&quot;EPSG&quot;,&quot;4326&quot;]]</SRS>
        #     <GeoTransform> -6.8000138888888884e+01,  2.7777777777777778e-04,  0.0000000000000000e+00,  1.9000138888888888e+01,  0.0000000000000000e+00, -2.7777777777777778e-04</GeoTransform>
        #   <Metadata domain="IMAGE_STRUCTURE">
        #     <MDI key="INTERLEAVE">PIXEL</MDI>
        #   </Metadata>
        # </PAMDataset>
        #

        aux_xml = '<PAMDataset><SRS>{0}</SRS>\
<GeoTransform>{1:E},  {2:E},  {3:E},  {4:E},  {5:E}, {6:E}</GeoTransform>\
<Metadata domain="IMAGE_STRUCTURE"><MDI key="INTERLEAVE">PIXEL</MDI></Metadata>\
</PAMDataset>'.format(projString, float(metaList[0]), float(metaList[4]), float(metaList[6]),
                      float(metaList[1]), float(metaList[7]), float(metaList[5]))


# print '{0:E} {1:E}'.format(1234567890, 1341234)
        # print '{:E} {:E}'.format(1234567890, 1341234)
        # aux_xml = '''
        # <PAMDataset>
        #   <SRS>{0}</SRS>
        #   <GeoTransform> {1},  {2},  {3},  {4},  {5}, {6}</GeoTransform>
        #   <Metadata domain="IMAGE_STRUCTURE">
        #     <MDI key="INTERLEAVE">PIXEL</MDI>
        #   </Metadata>
        # </PAMDataset>
        # '''.format(projString, metaList[0], metaList[4], metaList[6], metaList[1], metaList[7], metaList[5])


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

@app.route('/addpost', methods=['GET', 'POST'])
@login_required
def addpost():
    userID = long(g.user.get_id())
    if userID != 1:
        return redirect(url_for('index'))

    addNewPost = forms.NewPost()
    if request.method == "POST" and addNewPost.validate():
        postTitle = str(addNewPost.newPostTitle.data)
        postContent = str(addNewPost.newPostContent.data)

        theNewPost = models.Post(postTitle=postTitle, body=postContent, user_id=g.user.get_id())
        db_session.add(theNewPost)
        db_session.commit()
        return redirect(url_for('index'))
    else:
        return render_template('addPost.html', newPostForm=addNewPost, title='Add Post')

@app.route('/')
@app.route('/index')
def index():
    posts = db_session.query(models.Post).order_by(models.Post.id.desc())
    for p in posts:
        print p.body

    VALID_TAGS = ['strong', 'em', 'p', 'ul', 'li', 'br', 'b', 'i', 'code']

    try:
        post0Title = posts[0].postTitle
        soup0 = BeautifulSoup(str(posts[0].body).replace('\n', '<br/>'))
        for tag in soup0.findAll(True):
            if tag.name not in VALID_TAGS:
                tag.hidden = True
        post0Body = soup0.renderContents()

        post1Title = posts[1].postTitle
        soup1 = BeautifulSoup(str(posts[1].body).replace('\n', '<br/>'))
        for tag in soup1.findAll(True):
            if tag.name not in VALID_TAGS:
                tag.hidden = True
        post1Body = soup1.renderContents()
    except:
        post0Title = 'Title 1'
        post0Body = 'Body 1'
        post1Title = 'Title 2'
        post1Body = 'Body 2'

    return render_template('index.html', title='Home',
                           post0Title=post0Title, post0Body=post0Body,
                           post1Title=post1Title, post1Body=post1Body)


@app.route('/projects', methods=['GET', 'POST'])
@login_required
def getProjects():
    projform = forms.ProjectForm()
    if request.method == "POST" and projform.validate():
        projTID = int(request.form["proj_type"])
        if projTID == -1:
            flash('Select a project type.')
        else:
            newprojName = str(projform.projName.data)
            newproj = models.Project(tid=projTID, project_name=newprojName, usr=g.user)
            db_session.add(newproj)
            db_session.commit()

    projects_type_tuple = db_session.query(models.Project, models.Project_Type).\
        join(models.Project_Type).filter(models.Project.uid == int(g.user.uid))
    projectTypes = db_session.query(models.Project_Type).all()
    userProjectList = []
    for p in projects_type_tuple:
        userProjectList.append(p.Project.pid)
    session['userProjectList'] = userProjectList
    return render_template('projects.html',
                           title='Projects',
                           user_projects=projects_type_tuple,
                           projectTypes=projectTypes,
                           form=projform)

@app.route('/blog')
def blog():
    return render_template('blog.html', title='Open Terrain Map - Blog')

@app.route('/about')
def about():
    return render_template('about.html', title='Open Terrain Map - About')

@app.route('/contact')
def contact():
    return render_template('contact.html', title='Open Terrain Map - Contact')

@app.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('index'))
    form = forms.LoginForm()
    if form.validate_on_submit():
        session['remember_me'] = form.remember_me.data
        return oid.try_login(form.openid.data, ask_for = ['nickname', 'email'])
    return render_template('login.html',
                           title='Sign In',
                           form=form,
                           providers=app.config['OPENID_PROVIDERS'])

@oid.after_login
def after_login(resp):
    if resp.email is None or resp.email == "":
        flash('Invalid login. Please try again.')
        redirect(url_for('login'))
    user = db_session.query(models.User).filter_by(email=resp.email).first()

    if user is None:
        nickname = resp.nickname
        if nickname is None or nickname == "":
            nickname = resp.email.split('@')[0]
        user = models.User(nickname=nickname, email=resp.email, role=0)
        db_session.add(user)
        db_session.commit()
    remember_me = False
    if 'remember_me' in session:
        remember_me = session['remember_me']
        session.pop('remember_me', None)
    login_user(user, remember=remember_me)
    return redirect(request.args.get('next') or url_for('index'))

@lm.user_loader
def load_user(id):
    return db_session.query(models.User).get(int(id))

@app.before_request
def before_request():
    g.user = current_user

@app.route('/logout')
def logout():
    for key in session.keys():
        del session[key]
    logout_user()
    return redirect(url_for('index'))

@app.route('/map/getfeatures')
@login_required
def getfeatures():
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
        jsonstring += ',\n\t\t"geometry": ' + db_session.scalar(func.ST_AsGeoJSON(f.geom))
        jsonstring += ',\n' + f.getGeoJSONProps()
        jsonstring += '\n\t\t},\n'
    if hasFeats:
        jsonstring = jsonstring[:jsonstring.rfind(',')] + '\n'

    jsonstring += '\t]\n}'
    return jsonstring


@app.route('/setProject', methods=['POST'])
@login_required
def setProject():
    db_session.expunge_all()
    set_proj_success = False
    selected_pid = int(request.form["pid"])
    if selected_pid in session['userProjectList']:
        session['currentpid'] = selected_pid

        set_proj_success = True
    return jsonify(success=set_proj_success)

@app.route('/map', methods=['GET', 'POST'])
@login_required
def showmap():
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
        props['geom'] = db_session.scalar(func.ST_AsGeoJSON(thisproj.geom))
        print props['geom']

    session['currentProject'] = props

    jsonProps = simplejson.dumps(session['currentProject'])
    return render_template('map.html',
                           title=session['currentProject']['project_name'],
                           jsonProps=jsonProps)

@app.route('/map/addfeature', methods=['POST'])
@login_required
def addfeature():
    geomWKT = str(request.form["geomWKT"])
    srid_raw = str(request.form["srid"])
    # Just need the SRID number
    srid = long(srid_raw[srid_raw.find(':')+1:])
    geomType = str(request.form["geomType"]).upper()
    currentLayer = str(request.form["currentLayer"]).upper()

    newGeom = WKTElement(geomWKT, srid=srid)
    # Check the geometry before proceeding
    # geomSimple =  db_session.scalar(func.is_simple(newGeom))ST_IsValid
    geomValid = db_session.scalar(func.ST_IsValid(newGeom))
    # geomValid =  db_session.scalar(func.is_valid(newGeom))
    if not (geomValid):
        return jsonify(fid=-1,valid=False)

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

    return jsonify(fid=newFeature.fid, featureProperties=featureProperties)

@app.route('/map/editfeaturegeom', methods=['POST'])
@login_required
def editfeaturegeom():
    geomWKT = str(request.form["geomWKT"])
    # Just need the SRID number
    srid_raw = str(request.form["srid"])
    srid = long(srid_raw[srid_raw.find(':')+1:])
    featFID = long(request.form["fid"])

    newGeom = WKTElement(geomWKT, srid=srid)
    # Check the geometry before proceeding
    geomValid = db_session.scalar(func.ST_IsValid(newGeom))
    # geomSimple = db_session.scalar(func.is_simple(newGeom))
    # geomValid = db_session.scalar(func.is_valid(newGeom))
    if not geomValid:
        return jsonify(fid=-1)
    updateFeature = db_session.query(models.Feature).get(featFID)
    updateFeature.geom = newGeom
    db_session.commit()
    return jsonify(fid=featFID)

@app.route('/map/updateextent', methods=['POST'])
@login_required
def updateextent():
    # Task ids add: 1, modify:2, clear:3
    updateTask = int(request.form["updatetask"])
    if updateTask == 1 or updateTask == 2:
        geomWKT = str(request.form["geomWKT"])
        srid_raw = str(request.form["srid"])
        # Just need the SRID number
        srid = long(srid_raw[srid_raw.find(':')+1:])

        newGeom = WKTElement(geomWKT, srid=srid)
        # Check the geometry before proceeding
        # geomSimple =  db_session.scalar(func.is_simple(newGeom))
        # geomValid =  db_session.scalar(func.is_valid(newGeom))
        geomValid = db_session.scalar(func.ST_IsValid(newGeom))

        if not geomValid:
            return jsonify(code=-1)

        proj = db_session.query(models.Project).get(session['currentProject']['pid'])

        proj.geom = newGeom
        db_session.commit()
        # extentGeojson = db_session.scalar(func.ST_AsGeoJSON(newGeom))
        return jsonify(code=1)

    elif updateTask == 3:
        proj = db_session.query(models.Project).get(session['currentProject']['pid'])
        proj.geom = None
        db_session.commit()
        return jsonify(code=1)
    else:
        return jsonify(code=-2)

@app.route('/map/deletefeature', methods=['POST'])
@login_required
def deletefeature():
    # Task ids add: 1, modify:2, clear:3
    deleteFID = int(request.form["deleteFID"])
    deleteFeature = db_session.query(models.Feature).get(deleteFID)
    db_session.delete(deleteFeature)
    db_session.commit()
    return jsonify(success=0)

