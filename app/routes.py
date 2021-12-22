from flask import render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask.helpers import make_response
from app import app, db
from app.models import Tracker, TrackerScanner
from werkzeug.utils import secure_filename
import os
import json
import random

@app.before_first_request
def create_db():
    db.create_all()

@app.route("/", methods=['GET'])
def view_home():
    return render_template("dashboard.html", name = request.cookies.get("username"))

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        response = make_response(render_template("login.html"))
        response.set_cookie('username', expires=0)
        return response
    else:
        if "username" not in request.cookies or request.cookies.get("username") == '':
            flash("Please enter a username")
            return render_template("login.html")
        else:
            username = request.cookies.get("username")
            if(username != "Bhavya" and username != "Abby"):
                flash(f"No user {username}")
                return render_template("login.html")
            
            return redirect("/")

@app.route("/upload/<type>", methods=['GET', 'POST'])
def upload(type):
    if request.method == 'GET':
        if type == "tracker":
            return render_template("uploadTracker.html")
    else:
        if type == "tracker":
            data = json.loads(request.data)
            print(data)
            flash("Tracker saved successfully")
            return jsonify(status="success")

        if type == "img":
            image = request.files['image']
            if image.filename == '':
                flash('No image selected')
                return redirect("/upload/tracker")
            filename = secure_filename(image.filename)
            name = filename.split(".")[0]
            extension = filename.split(".")[1]
            filename = genRandomString(app.config["IMAGE_NAME_LENGTH"])+"."+extension
            if extension not in app.config["ALLOWED_EXTENSIONS"]:
                flash('image file type "'+extension+'" not supported')
                return redirect("/upload/tracker")
            path = os.path.join(app.root_path, app.config["IMAGE_UPLOADS_PATH"], filename)
            image.save(path)
            return redirect(url_for('edit_tracker', filename=filename))

@app.route("/images/<path:filename>", methods = ['GET'])
def get_image(filename):
    return send_from_directory(app.config["IMAGE_UPLOADS_PATH"], filename)

@app.route("/edit/tracker/<filename>", methods = ['GET'])
def edit_tracker(filename):
    path = os.path.join(app.root_path, app.config["IMAGE_UPLOADS_PATH"], filename)
    if(not os.path.isfile(path)):
        flash("tracker '" + filename + "' does not exist")

    # query db for tracker matching the filename and username

    tracker = TrackerScanner(path)
    try:
        tracker.scanTracker()
    except Exception as e:
        print(e)
        flash(e)
    
    data = tracker.data
    timesCompleted = []
    completionGoal = []
    numDaysInMonth = 31 # FIX AUTOMATICALLY
    for row in data:
        if 0.5 in row:
            timesCompleted.append(int(sum(row)*2))
            completionGoal.append(numDaysInMonth*2)
        else: 
            timesCompleted.append(sum(row))
            completionGoal.append(numDaysInMonth)
    table = []
    for i in range(14):
        activityName = "Click_to_edit_activity_name"
        if completionGoal[i]==numDaysInMonth*2:
            activityName = "Click_to_edit_activity_1 / Click_to_edit_activity_2"
        table.append({
            "activityName": activityName,
            "timesCompleted": timesCompleted[i],
            "completionGoal": completionGoal[i],
        })

    return render_template("editTracker.html", filename=filename, table=table)

@app.errorhandler(Exception)
def http_error_handler(error):
    return render_template("error.html")

def genRandomString(len):
    chars = 'abcdefghijklmnopqrstuvwxyz123456789'
    output = ''
    return ''.join(random.choice(chars) for i in range(len))