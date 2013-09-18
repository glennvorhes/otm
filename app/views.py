from flask import render_template, send_file, flash, redirect, session, url_for, request, g, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from app import app, db_session, lm, oid, models
import forms
from geoalchemy2.elements import WKTElement
from datetime import datetime
import simplejson
from sqlalchemy import func, desc
from bs4 import BeautifulSoup

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
    posts = db_session.query(models.Post).order_by(models.Post.timestamp.desc())

    VALID_TAGS = ['strong', 'em', 'p', 'ul', 'li', 'br', 'b', 'i', 'code']

    soup0 = BeautifulSoup(str(posts[0].body).replace('\n', '<br/>'))
    for tag in soup0.findAll(True):
        if tag.name not in VALID_TAGS:
            tag.hidden = True
    post0Body = soup0.renderContents()

    soup1 = BeautifulSoup(str(posts[1].body).replace('\n', '<br/>'))
    for tag in soup1.findAll(True):
        if tag.name not in VALID_TAGS:
            tag.hidden = True
    post1Body = soup1.renderContents()

    return render_template('index.html', title='Home',
                           post0Title=posts[0].postTitle, post0Body=post0Body,
                           post1Title=posts[1].postTitle, post1Body=post1Body)


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

    print thisproj.geom
    if not thisproj.geom is None:
        props['geom'] = db_session.scalar(func.ST_AsGeoJSON(thisproj.geom))
    else:
        props['geom'] = None

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
        return jsonify(fid=-1)

    proj = db_session.query(models.Project).get(session['currentProject']['pid'])

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
            print p, featureProperties[p]

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
            return jsonify(code=-1, extGSJN=None)

        proj = db_session.query(models.Project).get(session['currentProject']['pid'])

        proj.geom = newGeom
        db_session.commit()
        extentGeojson = db_session.scalar(func.ST_AsGeoJSON(newGeom))
        return jsonify(code=1, extGSJN=extentGeojson)

    elif updateTask == 3:
        proj = db_session.query(models.Project).get(session['currentProject']['pid'])
        proj.geom = None
        db_session.commit()
        return jsonify(code=1, extGSJN=None)
    else:
        return jsonify(code=-2, extGSJN=None)

@app.route('/map/deletefeature', methods=['POST'])
@login_required
def deletefeature():
    # Task ids add: 1, modify:2, clear:3
    deleteFID = int(request.form["deleteFID"])
    deleteFeature = db_session.query(models.Feature).get(deleteFID)
    db_session.delete(deleteFeature)
    db_session.commit()
    return jsonify(success=0)


#
# @app.route('/getelevtile')
# def getElevTile():
#     conn = None
#     try:
#         conn = psycopg2.connect(database="WebDevelop", user="postgres", password="turkey",
#                             host='localhost')
#
#         cur = conn.cursor()
#         cur.execute('select ST_AsPNG(ST_HillShade(ST_Transform(ST_AddBand(ST_Union(rast,1), ARRAY[ST_Union(rast,1)]), 3857),1,\'8BUI\',315,45,255,1)) from demelevation where (rid > 100 and rid < 105)')
#         ver = cur.fetchone()
#         print ver
#         return send_file(ver, mimetype='image/png')
#
#
#     except psycopg2.DatabaseError, e:
#         print 'Error %s' % e
#         sys.exit(1)
#
#
#     finally:
#
#         if conn:
#             conn.close()
#
#     return 'stuff'
