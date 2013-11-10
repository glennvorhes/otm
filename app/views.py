from flask import render_template, flash, redirect, session, url_for, request, g, jsonify
from flask_login import login_required
from app import app, models, DatabaseSessionMaker
import forms
from datetime import datetime
from bs4 import BeautifulSoup


@app.route('/ol3')
def ol3():
    return render_template('ol3.html')

@app.route('/')
@app.route('/index')
def index():
    db_session = DatabaseSessionMaker()
    posts = db_session.query(models.Post).order_by(models.Post.id.desc())

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
    db_session.close()
    return render_template('index.html', title='Home',
                           post0Title=post0Title, post0Body=post0Body,
                           post1Title=post1Title, post1Body=post1Body)


@app.route('/projects', methods=['GET', 'POST'])
@login_required
def getProjects():
    db_session = DatabaseSessionMaker()
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
    db_session.close()
    return render_template('projects.html',
                           title='Projects',
                           user_projects=projects_type_tuple,
                           projectTypes=projectTypes,
                           form=projform)


@app.route('/setProject', methods=['POST'])
@login_required
def setProject():
    db_session = DatabaseSessionMaker()
    db_session.expunge_all()
    set_proj_success = False
    selected_pid = int(request.form["pid"])
    if selected_pid in session['userProjectList']:
        session['currentpid'] = selected_pid
        set_proj_success = True

    db_session.close()
    return jsonify(success=set_proj_success)


@app.route('/tutorials')
def tutorials():
    show = request.args.get('show', '')
    page = request.args.get('page', '1')
    return render_template('tutorial.html', title='Tutorials', show=show, page=page)


@app.route('/about')
def about():
    show = request.args.get('show', 'motivation')
    return render_template('about.html', show=show, title='About')


@app.route('/contact')
def contact():
    return render_template('contact.html', title='Contact')


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
        db_session = DatabaseSessionMaker()
        db_session.add(theNewPost)
        db_session.commit()
        db_session.close()
        return redirect(url_for('index'))
    else:
        return render_template('addPost.html', newPostForm=addNewPost, title='Add Post')


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



