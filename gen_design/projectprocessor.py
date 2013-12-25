from app import DatabaseSessionMaker, models
from sqlalchemy import func
# from dwelling import Dwelling


class ProjectProcessor(object):

    def __init__(self, project_id):
        db_session = DatabaseSessionMaker()

        current_project = db_session.query(models.Project).get(project_id)
        feats = current_project.features
        db_session.close()



    def __repr__(self):
        print