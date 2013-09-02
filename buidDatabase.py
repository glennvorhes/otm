# Bail out of accidental run
# exit()

from app import db_session, metadata, models

# Clear and recreate database tables, relationships, etc
metadata.drop_all()
metadata.create_all()
#
# # Create two objects, define project types
sanitarySewerageProjectType = models.Project_Type(description='Simplified Sanitary Sewerage')
aqueductProjectType = models.Project_Type(description='Gravity Fed Water Supply')
#
# # Add to the database session (db_session)
db_session.add(sanitarySewerageProjectType)
db_session.add(aqueductProjectType)
#
# # Commit to the database
db_session.commit()
