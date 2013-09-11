from datetime import datetime
from app import Base
from sqlalchemy import Column, Integer, String, DateTime, SmallInteger, ForeignKey, Float
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry, Raster


class User(Base):
    __tablename__ = 'user'
    uid = Column(Integer, primary_key=True)
    nickname = Column(String(64), index=True, unique=True)
    email = Column(String(120), index=True, unique=True)
    role = Column(SmallInteger, default=0)
    posts = relationship('Post', backref='author', lazy='dynamic')
    projects = relationship('Project', backref='usr', lazy='dynamic')

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.uid)

    def __repr__(self):
        return '<User %r>' % (self.nickname)


class Feature(Base):
    __tablename__ = 'feature'
    fid = Column(Integer, primary_key=True)
    pid = Column(Integer, ForeignKey('project.pid'))
    created = Column(DateTime, default=datetime.now())
    discriminator = Column('type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    def getGeoJSONProps(self):
        outstring = '\t\t"properties": {\n'

        fieldList = (name for name in dir(self)
                        if not (name.startswith('_') or name in
                        ['metadata', 'geom', 'getGeoJSONProps', 'prj']))
        firstProp = True
        for field in fieldList:
            if firstProp:
                pref = ''
                firstProp = False
            else:
                pref = ',\n'
            attr = getattr(self, field)

            if not attr:
                outAttStr = 'null'
            elif type(attr) in [int, float]:
                outAttStr = str(attr)
            elif type(attr) is datetime:
                outAttStr = '"' + attr.strftime('%Y-%m-%d') + '"'
            else:
                outAttStr = '"' + str(attr) + '"'
            outstring += pref + '\t\t\t"' + field + '":' + outAttStr
        outstring += '\n\t\t\t}'
        return outstring


class Impedance(Feature):
    __tablename__ = 'impedance'
    __mapper_args__ = {'polymorphic_identity': 'impedance'}
    fid = Column(Integer, ForeignKey('feature.fid'), primary_key=True)
    impedance = Column(String(50))


class Impedance_LineString(Impedance):
    __tablename__ = 'impedance_linestring'
    __mapper_args__ = {'polymorphic_identity': 'impedance_linestring'}
    fid = Column(Integer, ForeignKey('impedance.fid'), primary_key=True)
    geom = Column(Geometry(geometry_type='LINESTRING', srid=3857, dimension=3))


class Impedance_Polygon(Impedance):
    __tablename__ = 'impedance_polygon'
    __mapper_args__ = {'polymorphic_identity': 'impedance_polygon'}
    fid = Column(Integer, ForeignKey('impedance.fid'), primary_key=True)
    geom = Column(Geometry(geometry_type='POLYGON', srid=3857, dimension=3))


class Dwelling(Feature):
    __tablename__ = 'dwelling'
    __mapper_args__ = {'polymorphic_identity': 'dwelling'}
    fid = Column(Integer, ForeignKey('feature.fid'), primary_key=True)
    owner = Column(String(50))
    occupants = Column(Integer, default=3)


class Dwelling_Point(Dwelling):
    __tablename__ = 'dwelling_point'
    __mapper_args__ = {'polymorphic_identity': 'dwelling_point'}
    fid = Column(Integer, ForeignKey('dwelling.fid'), primary_key=True)
    geom = Column(Geometry(geometry_type='POINT', srid=3857, dimension=3))


class Dwelling_Polygon(Dwelling):
    __tablename__ = 'dwelling_polygon'
    __mapper_args__ = {'polymorphic_identity': 'dwelling_polygon'}
    fid = Column(Integer, ForeignKey('dwelling.fid'), primary_key=True)
    geom = Column(Geometry(geometry_type='POLYGON', srid=3857, dimension=3))


class Tank_Site(Feature):
    __tablename__ = 'tank_site'
    __mapper_args__ = {'polymorphic_identity': 'tank_site'}
    fid = Column(Integer, ForeignKey('feature.fid'), primary_key=True)
    description = Column(String(50))
    geom = Column(Geometry(geometry_type='POLYGON', srid=3857, dimension=3))


class Treatment_Site(Feature):
    __tablename__ = 'treatment_site'
    __mapper_args__ = {'polymorphic_identity': 'treatment_site'}
    fid = Column(Integer, ForeignKey('feature.fid'), primary_key=True)
    description = Column(String(50))
    geom = Column(Geometry(geometry_type='POLYGON', srid=3857, dimension=3))


class Water_Source(Feature):
    __tablename__ = 'water_source'
    __mapper_args__ = {'polymorphic_identity': 'water_source'}
    fid = Column(Integer, ForeignKey('feature.fid'), primary_key=True)
    description = Column(String(50))
    flow_rate_gpm = Column(Float)
    geom = Column(Geometry(geometry_type='POINT', srid=3857, dimension=3))


class Project(Base):
    __tablename__ = 'project'
    pid = Column(Integer, primary_key=True)
    uid = Column(Integer, ForeignKey('user.uid'))
    tid = Column(Integer,ForeignKey('project_type.tid'))
    project_name = Column(String(50))
    created = Column(DateTime, default=datetime.now())
    last_modified = Column(DateTime, default=datetime.now())
    geom = Column(Geometry(geometry_type='POLYGON', srid=3857, dimension=2))
    features = relationship('Feature', backref='prj', lazy='dynamic')


class Project_Type(Base):
    __tablename__ = 'project_type'
    tid = Column(Integer, primary_key=True)
    description = Column(String(100))


class Post(Base):
    __tablename__ = 'post'
    id = Column(Integer, primary_key=True)
    body = Column(String(140))
    timestamp = Column(DateTime)
    user_id = Column(Integer, ForeignKey('user.uid'))

    def __repr__(self):
        return '<Post %r>' % (self.body)


class Raster_DEM(Base):
    __tablename__ = 'rawDEM'
    rid = Column(Integer, primary_key=True)
    rast = Column(Raster)
    filename = Column(String(50))


class DEM_Elevation(Base):
    __tablename__ = 'demelevation'
    rid = Column(Integer, primary_key=True)
    rast = Column(Raster)
    filename = Column(String(50))