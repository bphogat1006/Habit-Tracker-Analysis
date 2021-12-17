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
    filename = name+"_"+randomString(5)+"."+extension
    if extension not in app.config["ALLOWED_EXTENSIONS"]:
        flash('image file type "'+extension+'" not supported')
        return redirect("/upload")
    path = os.path.join(app.root_path, app.config["IMAGE_UPLOADS_PATH"], filename)
    image.save(path)
    return redirect("display/"+filename)

@app.route("/uploads/<path:filename>")
def get_image(filename):
    return send_from_directory(app.config["IMAGE_UPLOADS_PATH"], filename)

@app.route("/display/<filename>", methods = ['GET'])
def display_image(filename):
    path = os.path.join(app.root_path, app.config["IMAGE_UPLOADS_PATH"], filename)
    if(not os.path.isfile(path)):
        flash("image '" + filename + "' does not exist")

    tracker = TrackerScanner(path)
    try:
        tracker.scanTracker()
    except Exception as e:
        print(e)
        flash(e)
        return render_template('error.html')
    
    grid = tracker.data
    # activityNames = get_from_db
    totals = []
    filled = []
    numDaysInMonth = 31 # FIX AUTOMATICALLY
    for row in grid:
        if 0.5 in row:
            filled.append(int(sum(row)*2))
            totals.append(numDaysInMonth*2)
        else: 
            filled.append(sum(row))
            totals.append(numDaysInMonth)
    table = list()
    for i in range(14):
        activityName = "click_to_edit_activity_name"
        if totals[i]==numDaysInMonth*2:
            activityName = "click_to_edit_activity_1/click_to_edit_activity_2"
        table.append({
            "activityName": activityName,
            "timesCompleted": filled[i],
            "goal": totals[i],
            "ratio": str(round(filled[i]/totals[i]*100))+"%"
        })

    return render_template("display.html", filename=filename, table=table)

@app.route("/error", methods = ['GET'])
def error():
    return render_template("error.html")


def randomString(len):
    chars = 'abcdefghijklmnopqrstuvwxyz123456789'
    output = ''
    for i in range(len):
        output+=random.choice(chars)
    return output