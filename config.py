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
######## LocalHost ########
# SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:turkey@localhost:5432/webInfo'
# ConnStringDEM_DB = "dbname=OTM user=postgres password=turkey host=localhost port=5432"

######## Server database ########
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:turkey@192.168.0.101:5432/webInfo'
ConnStringDEM_DB = "dbname=OTM user=postgres password=turkey host=192.168.0.101 port=5432"

repositoryName = "db_repository"
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, repositoryName)