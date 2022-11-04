from sqlite3 import Connection as SQLite3Connection
from datetime import datetime
from sqlalchemy import event
from sqlalchemy.engine import Engine
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy

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
    
    return render_template("Bleatter.html", utc_dt="hello i'm a variable")

@app.route("/user", methods=["POST"]) # create user 
def create_user():
    # Question 1.1: create a request using json
    data = request.get_json()
    # Question 1.2: create a user
    new_user = User(username = data["username"],
                    email = data["email"],
                    location = data["location"],
                    pwd = data["password"]
                    )
    # add the user to the database
    db.session.add(new_user)
    # commit to the database
    db.session.commit() # take the entire session and update the 
    # database. 
    # Question 1.5: send the right message
    return jsonify({"message":"User created"}),200


@app.route("/register",methods=["POST","GET"])
def register():
    # request.form is a kind of dictionnary
    if request.method == "POST":
        information = request.form # get the form
        print("New user register")
        print(information["username"]) #what the new user fill in username field
        print(information["email"])
        print(information['location'])
        return
    
    return render_template("register.html")

@app.route("/users",methods=["GET"])
def get_all_users():
    pass
  
@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    app.env = "development"
    app.run(host="localhost", port="5000")