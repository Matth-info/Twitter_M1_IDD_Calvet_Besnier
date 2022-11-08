from sqlite3 import Connection as SQLite3Connection
from datetime import datetime
from sqlalchemy import event
from sqlalchemy.engine import Engine
from flask import Flask, request, jsonify, render_template, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import hashlib 

# app
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bleatter_database.file" # database storing all the created tables
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = 0

@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

db = SQLAlchemy(app)
now = datetime.now()

class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(24))
    email = db.Column(db.String(64))
    pwd = db.Column(db.String(64))
    location = db.Column(db.String(64))

class Tweet(db.Model):
    __tablename__ = "tweet"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256))
    content = db.Column(db.String(256))
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    like = db.Column(db.Integer)
    retweet = db.Column(db.Integer)
    reply = db.Column(db.Integer) #Pour l'instant c'est juste un compteur
                                  #On en fera une liste de reponse


@app.route("/")
def home():
    
    return render_template("Bleatter.html", var_mes ="Hi, Buddy Let's bleat together")

@app.route("/user", methods=["POST"]) # create user 
def create_user():
    # Question 1.1: create a request using json
    data = request.get_json()
    # Question 1.2: create a user
    new_user = User(username = data["username"],
                    email = data["email"],
                    location = data["location"],
                    pwd = hash_password(data["password"])
                    )
    # add the user to the database
    db.session.add(new_user)
    # commit to the database
    db.session.commit() # take the entire session and update the 
    # database. 
    # Question 1.5: send the right message
    return jsonify({"message":"User created"}),200


def hash_password(pwd):
    h = hashlib.sha256(str(pwd).encode('utf-8')) #we use sha256 hashfunction to hash the password
    return int(h.hexdigest(), base=16)
               
@app.route("/signup",methods=["POST","GET"])
def signup():
    # request.form is a kind of dictionnary
    if request.method == "GET" :
        return render_template("signup.html")
    
    else:
        data = request.form # get the form
        print(data)
        email = data["email"]
        username = data["username"]
        location = data["location"]
        pwd = data["password"]
        user = User.query.filter_by(email=email).first
        if user:
            flash('Email address already exists')
            return redirect(url_for("Main.signup"))
        new_user = User(email = email, username=username, location = location, pwd = hash_password(pwd))

        db.session.add(new_user) # add the user to the database
        db.session.commit()
        
        return render_template("Bleatter.html")
    

@app.route("/users",methods=["GET"])
def get_all_users():
    users = User.query.all()
    return jsonify([user.serialize() for user in users]), 200



@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    db.create_all()
    app.env = "development"
    app.run(host="localhost", port="5000")