import os

CSRF_ENABLED = True
SECRET_KEY = '3120ed6e-b1f8-11e2-b61d-001dd96bd028'

OPENID_PROVIDERS = [
    {'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id'},
    {'name': 'Yahoo', 'url': 'https://me.yahoo.com'},
    {'name': 'AOL',  'url': 'http://openid.aol.com/<username>'},
    {'name': 'Flickr', 'url': 'http://www.flickr.com/<username>'},
    {'name': 'MyOpenID', 'url': 'https://www.myopenid.com'}]

basedir = os.path.abspath(os.path.dirname(__file__))

#dialect+driver://username:password@host:port/database
# SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:turkey@localhost:5432/webInfo'
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:turkey@192.168.0.101:5432/webInfo'
repositoryName = "db_repository"
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, repositoryName)