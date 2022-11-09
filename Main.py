from sqlite3 import Connection as SQLite3Connection
from datetime import datetime
from sqlalchemy import event
from sqlalchemy.engine import Engine
from flask import Flask, request, jsonify, render_template, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import hashlib

# app
app = Flask(__name__)

# database storing all the created tables
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bleatter_database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = 0


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


db = SQLAlchemy(app)



class User(db.Model):
    __tablename__ = "User"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(24))
    email = db.Column(db.String(64))
    pwd = db.Column(db.String(64))
    location = db.Column(db.String(64))
    
    def serialize(self):
        return { "id" : self.id, "name" : self.username , "email" : self.email,"location" : self.location, "password ": self.pwd}
    


class Tweet(db.Model):
    __tablename__ = "Tweet"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256))
    content = db.Column(db.String(256))
    author_id = db.Column(db.Integer, db.ForeignKey("User.id"), nullable=False)
    like = db.Column(db.Integer)
    retweet = db.Column(db.Integer)
    reply = db.Column(db.Integer)  # Pour l'instant c'est juste un compteur
    # On en fera une liste de reponse


@app.route("/")
def home():
    return render_template("Bleatter.html")


@app.route("/user", methods=["POST"])  # create user
def create_user():
    data = request.get_json()
    new_user = User(username=data["username"],
                    email=data["email"],
                    location=data["location"],
                    pwd= hash_password(data["password"])
                    )
    # add the user to the database
    db.session.add(new_user)
    # commit to the database
    db.session.commit()  # take the entire session and update the
    # database.
    return jsonify({"message": "User created"}), 200


def hash_password(pwd):
    # we use sha256 hashfunction to hash the password
    h = hashlib.sha256(str(pwd).encode('utf-8'))
    return str(int(h.hexdigest(), base=16))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    # request.form is a kind of dictionnary
    if request.method == "GET":
        return render_template("signup.html")

    else:
        email = request.form ["email"]
        username = request.form ["username"]
        location = request.form ["location"]
        pwd = request.form ["password"]
        pwd_c = request.form ["password_c"]

        if (pwd != pwd_c):
            flash("Passwords are different")
            return redirect(url_for("signup"))

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists')
            return redirect(url_for("Main.signup"))
        else:
            new_user = User(email=email, username=username,
                            location=location, pwd=hash_password(pwd))
            db.session.add(new_user)
            db.session.commit()
            flash("Record was successfully added")
            return render_template("Bleatter.html")  # put signin


@app.route("/users", methods=["GET"])
def get_all_users():
    users = User.query.all()
    return jsonify([user.serialize() for user in users]), 200


@app.route("/about")
def about():
    return render_template("about.html")


if __name__ == "__main__":
    app.secret_key = "012345"
    with app.app_context():
        db.create_all()
    app.env = "development"
    app.run(host="localhost", port="5000")
