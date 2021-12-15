from flask import Flask
import os

app = Flask(__name__)
app.config["IMAGE_UPLOADS_PATH"] = "static\\uploads"
app.config["ALLOWED_EXTENSIONS"] = {'png', 'jpg', 'jpeg'}
app.config["SECRET_KEY"] = os.urandom(24)

from app import routes, models