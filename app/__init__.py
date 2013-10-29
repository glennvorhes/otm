from flask import Flask
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from config import basedir
import os
from flask.ext.login import LoginManager
from flask.ext.openid import OpenID
from flask.ext.babel import Babel

# Application init, here named 'app'
app = Flask(__name__)
app.config.from_object('config')
# Babel used for automatic language translations
# Not implemented yet
babel = Babel(app)

#Configuration for SQLAlchemy
# Database location, username, and password defined elsewhere
# Accessed here by app.config['SQLALCHEMY_DATABASE_URI']
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], echo=False)
DatabaseSessionMaker = sessionmaker(bind=engine)

# Define models base
metadata = MetaData(engine)
Base = declarative_base(metadata=metadata)

#db_session object used for all database interaction
# Insert, update, delete
# Nothing happens at the database until call to db_session.commit()
# db_session = Session()

# Not to be confused with 'session' object which is declared globally
# as a part of the Flask application
# This is very important and is used to store variables is used to keep
# track of a specific user between requests
# stores information as a dictionary
# For example session['name'] = 'Glenn'
# Can retrieve session['name'] on subsequent requests
# In flask (werkzeug session) no need to call session.save() as with
# other session managers. ex Beaker

# Login manager init
lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'

# OpenID needs a scratch directory, define location here
oid = OpenID(app, os.path.join(basedir, 'tmp'))
tempZipDir = os.path.join(basedir, 'tmp/tempzip')

# import other modules so they can be accessed from 'app'
from app import models, views, map_views, login_views, example_views, get_dem_view




