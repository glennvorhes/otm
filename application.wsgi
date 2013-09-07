#activate_this = '/home/webserver/flask/bin/activate_this.py'
#execfile(activate_this, dict(__file__=activate_this))

#import sys
#sys.path.insert(0, '/home/webserver/OTM')

#from app import app as application

def application(environ, start_response):
    status = '200 OK'

    if not environ['mod_wsgi.process_group']:
      output = 'EMBEDDED MODE'
    else:
      output = 'DAEMON MODE'

    response_headers = [('Content-Type', 'text/plain'),
                        ('Content-Length', str(len(output)))]

    start_response(status, response_headers)

    return [output]