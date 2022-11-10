
from sqlite3 import Connection as SQLite3Connection
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   url_for, g, session)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
import datetime
import hashlib
from data_struct import *


# app
app = Flask(__name__)
app.secret_key = "012345"

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
    def __repr__(self):
        return  '<Id %r>' %self.id +  '<Name %r>' % self.username + '<email %r>' % self.email + '<location %r>' % self.location


class Bleat(db.Model):
    __tablename__ = "Bleat"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256))
    content = db.Column(db.String(256))
    author_id = db.Column(db.Integer, db.ForeignKey("User.id"), nullable=False)
    like = db.Column(db.Integer)
    retweet = db.Column(db.Integer)
    reply = db.Column(db.Integer)  # Pour l'instant c'est juste un compteur, on en fera une liste de reponse
    date = db.Column(db.String(256))

    def serialize(self):
        return {"title": self.title, "content": self.content}


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

@app.route("/users/<int:ID>",methods=["GET","POST","DELETE"])
def users(ID):
    users = User.query.all()
    
    if (request.method == "GET"):
        user = User.query.filter_by(id = ID).first()
        if user:    
            return jsonify(user.serialize()), 200
        else:
            return jsonify({"message":" No student found"}), 201
    
    elif (request.method == "POST"):
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
    else: 
        user_del = User.query.filter_by(id = ID).first()
        if user_del:    
            db.session.delete(user_del)
            db.session.commit()
            return jsonify({"message": "successfully deleted"}) , 200
        else:
            return jsonify({"message": "user not found"}), 201

@app.route("/bleat", methods=["POST"])
def create_bleat():
    data = request.get_json()
    new_bleat = Bleat(title = data["title"],
                    content = data["content"],
                    author_id = data["author_id"],
                    like = data["like"],
                    retweet = data["retweet"],
                    reply = data["reply"],
                    date = datetime.datetime.now()
                    )

    db.session.add(new_bleat)
    db.session.commit()
    return jsonify({"message": "Bleat created"}), 200

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
            flash("Passwords are different","info")
            return redirect(url_for("signup"))

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists',"info")
            return redirect(url_for("signup"))
        else:
            new_user = User(email=email, username=username,
                            location=location, pwd=hash_password(pwd))
            db.session.add(new_user)
            db.session.commit()
            flash("Record was successfully added","info")
            return render_template("signin.html"), 200  # put signin

@app.route("/signin", methods=["GET", "POST"])
def signin():

    if request.method == "GET":
        return render_template("signin.html")

    else:
        email = request.form["email"]
        password = request.form["password"] #Recuperation du form

    user = User.query.filter_by(email=email).first() #Check if user exist
    if user:
        if hash_password(password) == user.pwd: #If yes check if this is the right password
            session["current_user"] = user.id # the session.current_user keep the id user, it will be custom the user experience 
            return render_template("post_a_bleat.html") 
        else:
            flash("Wrong password")
            return render_template("signin.html")
    else:
        flash("User don't exist")
        return render_template("signin.html")

@app.route("/logout")
def logout():
    session.pop("current_user",None)
    return redirect(url_for("home"))

@app.route("/post_a_bleat", methods=["GET","POST"])
def post_a_bleat():
    if request.method == "GET":
        return render_template("post_a_bleat.html")
    else:
        id_user = session.get('current_user',None)
        if id_user is None:
            render_template("signin.html")
        else:
            #id_user = request.form["id"]
            title = request.form["title"]
            content = request.form["content"]

            user = User.query.filter_by(id=id_user).first() # get the user associated to the id
            if not user:
                flash("User with " + id_user + " does not exist")
                return render_template("post_a_bleat.html")
            else:
                new_bleat = Bleat(title = title, content = content, author_id = int(id_user)
                ,like=0,retweet=0,reply=0, date = datetime.datetime.now())

                db.session.add(new_bleat)
                db.session.commit()
                flash("Message was successfully added","info")
                return redirect(url_for("home"))


@app.route("/users", methods=["GET"])
def get_all_users():
    users = User.query.all()
    return jsonify([user.serialize() for user in users]), 200


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/home_page", methods=["GET"])
def home_user():
    if request.method == "GET":
        bleats = Bleat.query.all()
        message = []
        name = []
        date = []
        for t in bleats:
            name.append(User.query.filter_by(id = t.author_id).first().username)
            message.append(t.title +": " + t.content)
            date.append("le " + t.date[0:10] + " à " + t.date[11:19])
        return render_template("home_page.html", len = len(message), message=message, name=name, date=date)


if __name__ == "__main__":

    with app.app_context():
        db.create_all()
    app.env = "development"
    app.run(host="localhost", port="5000")
