# Script to fill the database


from sqlalchemy import and_
from lorem_text import lorem
import random
from names_dataset import NameDataset
import sys
from sqlite3 import Connection as SQLite3Connection
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   url_for, g, session)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
import datetime
import hashlib
from data_struct import *

from sqlalchemy import PrimaryKeyConstraint, CheckConstraint
import tweepy
# app
app = Flask(__name__)
app.secret_key = "012345"

# database storing all the created tables
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bleatter_database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = 0
db = SQLAlchemy(app)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


class Bleat(db.Model):
    __tablename__ = "Bleat"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256))
    content = db.Column(db.String(256))
    author_id = db.Column(db.Integer, db.ForeignKey("User.id"), nullable=False)
    like = db.Column(db.Integer)
    retweet = db.Column(db.Integer)
    # Pour l'instant c'est juste un compteur, on en fera une liste de reponse
    reply = db.Column(db.Integer)
    date = db.Column(db.String(256))

    def serialize(self):
        return {"title": self.title, "content": self.content}


class User(db.Model):
    __tablename__ = "User"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(24))
    email = db.Column(db.String(64))
    pwd = db.Column(db.String(64))
    location = db.Column(db.String(64))

    def serialize(self):
        return {"id": self.id, "name": self.username, "email": self.email, "location": self.location, "password ": self.pwd}

    def __repr__(self):
        return '<Id %r>' % self.id + '<Name %r>' % self.username + '<email %r>' % self.email + '<location %r>' % self.location


class Relationship(db.Model):
    __tablename__ = "Relationship"
    id = db.Column(db.Integer, primary_key=True)
    userID1 = db.Column(db.Integer, db.ForeignKey("User.id"), nullable=False)
    userID2 = db.Column(db.Integer, db.ForeignKey("User.id"), nullable=False)
    CheckConstraint("userID1 != userID2", name="check1")
    date = db.Column(db.String(256))
    pending = db.Column(db.Boolean)


def hash_password(pwd):
    # we use sha256 hashfunction to hash the password
    h = hashlib.sha256(str(pwd).encode('utf-8'))
    return str(int(h.hexdigest(), base=16))


def generate_users(n=100):
    location = ["Los Angeles", "New York", "San Fransisco", "Dallas",
                "San Jose", "San Diego", "Houston", "Chicago", "Las Vegas", "Portland"]
    nd = NameDataset()
    M = nd.get_top_names(n=50, gender='Male', country_alpha2='US')['US']["M"]
    F = nd.get_top_names(n=50, gender='Female', country_alpha2='US')["US"]["F"]
    for i in range(n):
        g = random.randint(0, 1)
        n = random.randint(0, len(F)-1)
        l = random.randint(0, len(location)-1)
        if g == 0:
            username = M[n]
        else:
            username = F[n]
        email = str(username[0] + str(random.randint(1, 100)) + "@gmail.com")
        pwd = hash_password(str(username[0] + username[len(username)-1]))

        new_user = User(username=username, email=email,
                        pwd=pwd, location=location[l])
        print(new_user.username + "lives in " + new_user.location)
        db.session.add(new_user)
        # commit to the database
        db.session.commit()
    return "success"


def generate_bleat(n=1000):
    size = len(User.query.all())
    for i in range(n):
        author_id = random.randint(1, size - 1)
        if User.query.filter_by(id=author_id).first():
            content = lorem.words(10)
            title = lorem.words(1)
            like = random.randint(0, 100)
            retweet = random.randint(0, 10)
            reply = 0  # Pour l'instant c'est juste un compteur, on en fera une liste de reponse
            date = datetime.datetime.now()
            new_bleat = Bleat(title=title, content=content, author_id=author_id,
                              like=like, retweet=retweet, reply=reply, date=date)
            db.session.add(new_bleat)
            db.session.commit()
    return "success"


def generate_relationship(n=200):
    size = len(User.query.all())
    for i in range(n):
        id1, id2 = random.randint(1, size-1), random.randint(1, size-1)
        if not db.session.query(Relationship).filter(and_(Relationship.userID1 == id1, Relationship.userID2 == id2)).first():
            if id1 != id2 and User.query.filter_by(id=id1).first() and User.query.filter_by(id=id2).first():
                p = bool(random.randint(0, 1))
                date = datetime.datetime.now()
                if p is True:

                    db.session.add(Relationship(
                        userID1=id1, userID2=id2, date=date, pending=p))
                    db.session.add(Relationship(
                        userID1=id2, userID2=id1, date=date, pending=p))
                else:
                    db.session.add(Relationship(
                        userID1=id1, userID2=id2, date=date, pending=p))
                db.session.commit()
    return "success"

if __name__ == "__main__":
    # print(generate_users())
    # print(generate_bleat())
    # print(generate_relationship())