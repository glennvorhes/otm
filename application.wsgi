activate_this = '/home/webserver/flask/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

from app import app as application