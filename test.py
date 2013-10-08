print '{0:E} {1:E}'.format(1234567890, 1341234)



print 'here'
#
# import socket
#
# try:
#     socket.inet_aton('192.163.0.110')
#     print 'here'
# except socket.error:
#     print 'not here'

# import app
# from app import db_session, models
# from geoalchemy2.elements import RasterElement
# from sqlalchemy.orm import joinedload
# from app.models import Dwelling_Point, User, Post, Impedance_LineString, Impedance_Polygon, Feature, Water_Source, Project_Type, Project
# import subprocess, os
# from datetime import datetime
# print os.getcwd()
# os.chdir('/home/glenn/Desktop/dems')
# print os.getcwd()
# r = db_session.query(models.DEM_Elevation).get(5)
# print type(r.rast)
# print type(r.rast.data)
# print r.rid

# newRastElement = RasterElement(r.rast.data)

# subprocess.call('raster2pgsql -s 4236 -I -a -M *.tif -F  public.rawdem > elev9.sql')
#
# # subprocess.call('ls')

# raster2pgsql -s 4236 -I -C -M *.tif -F -t 100x100 public.demelevation | psql -d webInfo -h localhost -p 5432
# Add new comment
# doReload = True
#
# if doReload:
#     app.metadata.drop_all()
#     # exit()
#     app.metadata.create_all()
#
#     san = Project_Type(description='Simplified Sanitary Sewerage')
#     aq = Project_Type(description='Gravity Fed Water Supply')
#     db_session.add(san)
#     db_session.add(aq)
#     db_session.commit()
#     exit()



# firstusr = db_session.query(User).get(1)

# p.geom = WKTSpatialElement("POLYGON((-81.3 37.2, -80.63 38.04, -80.02 37.49, -81.3 37.2))", 4326)
# ob = db_session.query(Feature).get(5)
# db_session.delete(ob)
# db_session.commit()

# p = db_session.query(Project).get(2)
# p.geom = WKTSpatialElement("POLYGON((-81.3 37.2, -80.63 38.04, -80.02 37.49, -81.3 37.2))", 4326)
# # #
# lineimped1 =WKTSpatialElement("LINESTRING(-80.3 38.2, -81.03 38.04, -81.2 37.89)", 4326)
# imp1 = Impedance_LineString(geom=lineimped1,prj=p)
# polyimped1 = WKTSpatialElement("POLYGON((-81.3 37.2, -80.63 38.04, -80.02 37.49, -81.3 37.2))", 4326)
# imp3 = Impedance_Polygon(geom=polyimped1,prj=p)
# lineimped1 =WKTSpatialElement("POINt(-81.3 38.2)", 4326)
# dw = Dwelling_Point(geom=lineimped1, prj=p)
# db_session.add_all([imp1,imp3,dw])
#
#
# h = db_session.query(Project).get(1)
# h.geom = None
# db_session.commit()
# print 'committed'
#
# exit()
# polyimped1 = WKTSpatialElement("POLYGON((-81.3 37.2, -80.63 38.04, -80.02 37.49, -81.3 37.2))", 4326)
# imp3 = Impedance_Polygon(geom=polyimped1)
# imp4 = Impedance_LineString(geom=lineimped1)
#
#
# wt = WKTSpatialElement('POINT(-82 38)',4326)
# wtr = Water_Source(geom=wt, flow_rate_gpm=10.5)

# db_session.add(imp1)
# db_session.add(imp3)
# db_session.add(imp4)
#
# db_session.add(wtr)
# db_session.commit()

# feats = db_session.query(Feature).all()

# jsonstring =  '{ "type": "FeatureCollection",\n\t"features": [\n'
# for ft in feats:
#     jsonstring += '\t\t{\n\t\t"type": "Feature",\n'
#     jsonstring += '\t\t"geometry": ' + db_session.scalar(pg_functions.geojson(ft.geom)) + ',\n'
#     jsonstring += ft.getGeoJSONProps()
#     jsonstring +='\n\t\t},\n'
#
# jsonstring = jsonstring[:jsonstring.rfind(',')] +'\n'
# jsonstring += '\t]\n}'
# print jsonstring


#
# wkt_lake1 = WKTSpatialElement("POLYGON((-81.3 37.2, -80.63 38.04, -80.02 37.49, -81.3 37.2))", 4326)
# print 'simple', db_session.scalar(wkt_lake1.is_simple)

# u = db_session.query(User).first()
# p = Post(body='my first post!', timestamp=datetime.utcnow(), author=u)
# db_session.add(p)
# db_session.commit()



# print 'pg simple1', db_session.scalar(pg_functions.is_simple(point))

# db_session.expunge_all()
#
# for ob in db_session:
#     print 'any'


# exit()





