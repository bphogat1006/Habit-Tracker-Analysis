from calendar import month
import enum
from flask import render_template, request, redirect, url_for, flash, send_from_directory, make_response, jsonify
from app import app, db
from app.models import Tracker
from app.trackerScanner import TrackerScanner
from werkzeug.utils import secure_filename
from calendar import month_name
import os
import json
import random

@app.before_first_request
def create_db():
    db.create_all()

@app.route("/", methods=['GET'])
def view_home():
    currUser = request.cookies.get("username")
    secondUser = "Bhavya" if currUser=="Abby" else "Abby"

    currUserTrackers = Tracker.query.filter_by(user=currUser).all()
    secondUserTrackers = Tracker.query.filter_by(user=secondUser).all()

    for i, tracker in enumerate(currUserTrackers):
        currUserTrackers[i] = {
            "filename": tracker.filename,
            "percentFinished": tracker.percentFinished,
            "month": tracker.month,
            "year": tracker.year
        }
    for i, tracker in enumerate(secondUserTrackers):
        secondUserTrackers[i] = {
            "filename": tracker.filename,
            "percentFinished": tracker.percentFinished,
            "month": tracker.month,
            "year": tracker.year
        }

    print(currUserTrackers, secondUserTrackers)

    trackerList = []
    for currTracker in currUserTrackers:
        currMonth = currTracker.get("month")
        currYear = currTracker.get("year")
        for secondTracker in secondUserTrackers:
            if currMonth == secondTracker.get("month") and currYear == secondTracker.get("year"):
                winner = winnerPercentage = None
                if currTracker.get("percentFinished") > secondTracker.get("percentFinished"):
                    winner = currUser
                    winnerPercentage = currTracker.get("percentFinished")
                elif currTracker.get("percentFinished") < secondTracker.get("percentFinished"):
                    winner = secondUser
                    winnerPercentage = secondTracker.get("percentFinished")
                else:
                    winner = "TIE"
                    winnerPercentage = secondTracker.get("percentFinished")
                trackerList.append({
                    "winner": winner,
                    "percentFinished": winnerPercentage,
                    "month": currMonth,
                    "year": currYear,
                    "currTrackerFile": currTracker.get("filename"),
                    "secondTrackerFile": secondTracker.get("filename")
                })

    monthToInt = {month: index for index, month in enumerate(month_name) if month}
    trackerList.sort(key=lambda t: (t.get("year"), monthToInt[t.get("month")]), reverse=True)

    return render_template("dashboard.html", name=currUser, trackerList=trackerList)

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

@app.route("/images/<path:filename>", methods = ['GET'])
def get_image(filename):
    return send_from_directory(app.config["IMAGE_UPLOADS_PATH"], filename)

@app.route("/upload/<type>", methods=['GET', 'POST'])
def upload(type):
    if request.method == 'GET':
        if type == "tracker":
            return render_template("uploadTracker.html")
    else:
        if type == "tracker":
            response = None
            try:
                data = json.loads(request.data)
                tracker = Tracker(
                    user = str(data['user']),
                    filename = str(data.get('filename')),
                    month = str(data.get('month')),
                    year = str(data.get('year')),
                    percentFinished = str(data.get('percentFinished')),
                    trackerData = json.dumps(data.get('trackerData'))
                )
                # delete trackers in db of the current user if either the filename matches or the month/year matches
                Tracker.query.filter((Tracker.user==tracker.user) & ((Tracker.filename==tracker.filename) | ((Tracker.month==tracker.month) & (Tracker.year==tracker.year)))).delete()
                db.session.add(tracker)
                db.session.commit()

                flash("Tracker saved successfully")
                print("Tracker saved successfully")
                response = make_response(jsonify({'code': 'SUCCESS'}), 201)
            except Exception as e:
                app.config['ERROR_HOLDER'] = str(e)
                print("Tracker failed to save\n",e)
                response = make_response(jsonify({'code': 'FAILURE', 'error':str(e)}), 400)
            return response

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

@app.route("/error", methods = ['GET'])
def error():
    e = app.config['ERROR_HOLDER']+""
    app.config['ERROR_HOLDER'] = ''
    print("ERROR HANDLED: ",e)
    return render_template("error.html", custom_error = e)

def genRandomString(len):
    chars = 'abcdefghijklmnopqrstuvwxyz123456789'
    output = ''
    return ''.join(random.choice(chars) for i in range(len))