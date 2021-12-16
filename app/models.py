
from app import db
from calendar import month_name

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)

class Tracker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datecreated = db.Column(db.DateTime, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    filename = db.Column(db.String(255), nullable=False)

    def getMonth(self):
        month_name[self.month]