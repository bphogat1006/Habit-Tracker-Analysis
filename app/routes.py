from flask import render_template, request, redirect, url_for, flash, send_from_directory
from app import app, db
from app.models import Tracker, TrackerScanner
from werkzeug.utils import secure_filename
import os
import random

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
    name = filename.split(".")[0]
    extension = filename.split(".")[1]
    filename = genRandomString(8)+"."+extension
    if extension not in app.config["ALLOWED_EXTENSIONS"]:
        flash('image file type "'+extension+'" not supported')
        return redirect("/upload")
    path = os.path.join(app.root_path, app.config["IMAGE_UPLOADS_PATH"], filename)
    image.save(path)
    return redirect("edit/tracker/"+filename)

@app.route("/uploads/<path:filename>", methods = ['GET'])
def get_image(filename):
    return send_from_directory(app.config["IMAGE_UPLOADS_PATH"], filename)

@app.route("/edit/tracker/<filename>", methods = ['GET'])
def edit_tracker(filename):
    path = os.path.join(app.root_path, app.config["IMAGE_UPLOADS_PATH"], filename)
    if(not os.path.isfile(path)):
        flash("image '" + filename + "' does not exist")

    tracker = TrackerScanner(path)
    try:
        tracker.scanTracker()
    except Exception as e:
        print(e)
        flash(e)
    
    grid = tracker.data
    # activityNames = get_from_db
    timesCompleted = []
    completionGoal = []
    numDaysInMonth = 31 # FIX AUTOMATICALLY
    for row in grid:
        if 0.5 in row:
            timesCompleted.append(int(sum(row)*2))
            completionGoal.append(numDaysInMonth*2)
        else: 
            timesCompleted.append(sum(row))
            completionGoal.append(numDaysInMonth)
    table = list()
    for i in range(14):
        activityName = "Click_to_edit_activity_name"
        if completionGoal[i]==numDaysInMonth*2:
            activityName = "Click_to_edit_activity_1 / Click_to_edit_activity_2"
        table.append({
            "activityName": activityName,
            "timesCompleted": timesCompleted[i],
            "completionGoal": completionGoal[i],
            "percentFinished": str(round(timesCompleted[i]/completionGoal[i]*100))+"%"
        })

    return render_template("editTracker.html", filename=filename, table=table)

@app.errorhandler(Exception)
def http_error_handler(error):
    return render_template("error.html")

def genRandomString(len):
    chars = 'abcdefghijklmnopqrstuvwxyz123456789'
    output = ''
    return ''.join(random.choice(chars) for i in range(len))