from sqlite3 import Connection as SQLite3Connection
from datetime import datetime
from sqlalchemy import event
from sqlalchemy.engine import Engine
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

# app
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///sqlitedb.file"
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
    f = open("Bleatter.html", "r")
    home = f.read()
    f.close()
    return home

if __name__ == "__main__":
    app.run(host="localhost", port="5000")