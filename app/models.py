from app import app, db
from datetime import datetime

class Tracker(db.Model):
    # metadata
    __tablename__ = 'Trackers'
    id = db.Column(db.Integer, primary_key=True)
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # Tracker data
    user = db.Column(db.String(20), nullable=False)
    filename = db.Column(db.String(5+app.config["IMAGE_NAME_LENGTH"]), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    percentFinished = db.Column(db.Integer, nullable=False)
    trackerData = db.Column(db.String(5000), nullable=False)

    def __repr__(self):
        return f"Tracker for user {self.user} from {self.month} {self.year} is {self.percentFinished}% completed."