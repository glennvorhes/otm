activate_this = '/home/webserver/flask/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

import sys, os
#sys.path.insert(0, "/home/webserver/OTM")
sys.path.insert(0, str(os.getcwd()))

from app import app as application
