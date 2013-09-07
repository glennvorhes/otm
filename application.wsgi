activate_this = '/home/webserver/flask/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

import sys, os
sys.path.insert(0, os.getcwd())

from app import app as application
