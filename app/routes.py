from flask import render_template, request, redirect, url_for, flash
from app import app, db
from app.models import Tracker, Test
from werkzeug.utils import secure_filename
import os

@app.before_first_request
def create_db():
    db.create_all()

@app.route("/", methods=['GET'])
def view_home():

    return render_template("home.html")
    
@app.route("/upload", methods=['GET'])
def view_upload_page():
    return render_template("upload.html")

@app.route("/uploader", methods = ['POST'])
def upload_file():
    image = request.files['image']
    if image.filename == '':
        flash('No image selected')
        return redirect("/upload")
    filename = secure_filename(image.filename)
    fileExtension = filename.split(".")[1]
    if fileExtension not in app.config["ALLOWED_EXTENSIONS"]:
        flash('image file type "'+fileExtension+'" not supported')
        return redirect("/upload")
    path = os.path.join(app.root_path, app.config["IMAGE_UPLOADS_PATH"], filename)
    image.save(path)
    return redirect("display/"+filename)

@app.route("/display/<filename>", methods = ['GET'])
def display_image(filename):
    path = os.path.join(app.root_path, app.config["IMAGE_UPLOADS_PATH"], filename)
    print(os.path.isfile(path))
    if(not os.path.isfile(path)):
        flash("image '" + filename + "' does not exist")

    
    return render_template("display.html", filename="uploads/"+filename)

def randomString(len):
    chars = 'abcdefghijklmnopqrstuvwxyz123456789'
    output = ''.join(char for char in chars)
    return output