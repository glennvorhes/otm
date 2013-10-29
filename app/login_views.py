from flask import render_template, flash, redirect, session, url_for, request, g
from flask_login import login_user, logout_user, current_user
from app import app, lm, oid, models, DatabaseSessionMaker
import forms


@app.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('index'))
    form = forms.LoginForm()
    if form.validate_on_submit():
        session['remember_me'] = form.remember_me.data
        return oid.try_login(form.openid.data, ask_for=['nickname', 'email'])
    return render_template('login.html',
                           title='Sign In',
                           form=form,
                           providers=app.config['OPENID_PROVIDERS'])


@oid.after_login
def after_login(resp):
    db_session = DatabaseSessionMaker()
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
    db_session.close()
    return redirect(request.args.get('next') or url_for('index'))


@lm.user_loader
def load_user(id):
    db_session = DatabaseSessionMaker()
    userid =  db_session.query(models.User).get(int(id))
    db_session.close()
    return userid


@app.before_request
def before_request():
    g.user = current_user


@app.route('/logout')
def logout():
    for key in session.keys():
        del session[key]
    logout_user()
    return redirect(url_for('index'))
