# Script to fill the database


from data_struct import LinkedList
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
import networkx as nx
import matplotlib.pyplot as plt
from sqlalchemy import PrimaryKeyConstraint, CheckConstraint
from Levenshtein import distance

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


class User(db.Model):
    __tablename__ = "User"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(24))
    email = db.Column(db.String(64))
    pwd = db.Column(db.String(64))
    location = db.Column(db.String(64))
    bleats = db.relationship(
        "Bleat", passive_deletes=True, cascade="all, delete")

    def serialize(self):
        return {"id": self.id, "name": self.username, "email": self.email, "location": self.location, "password ": self.pwd}

    def __repr__(self):
        return '<Id %r>' % self.id + '<Name %r>' % self.username + '<email %r>' % self.email + '<location %r>' % self.location


class Bleat(db.Model):
    __tablename__ = "Bleat"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256))
    content = db.Column(db.String(256))
    author_id = db.Column(db.Integer, db.ForeignKey(
        "User.id", ondelete='CASCADE'), nullable=False)
    like = db.Column(db.Integer)
    retweet = db.Column(db.Integer)
    # for now it's just a counter, we will do a response list
    reply = db.Column(db.Integer)
    date = db.Column(db.String(256), nullable=False)

    def serialize(self):
        return {"title": self.title, "content": self.content}


class Relationship(db.Model):
    __tablename__ = "Relationship"
    userID1 = db.Column(db.Integer, db.ForeignKey(
        "User.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    userID2 = db.Column(db.Integer, db.ForeignKey(
        "User.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    date = db.Column(db.String(256), nullable=False)
    pending = db.Column(db.Boolean, nullable=False)


class Like(db.Model):
    __tablename__ = "Like"
    bleat_id = db.Column(db.Integer, db.ForeignKey(
        Bleat.id, ondelete='CASCADE'), nullable=False, primary_key=True)  # Bleat liked
    liker_id = db.Column(db.Integer, db.ForeignKey(
        User.id, ondelete='CASCADE'), nullable=False, primary_key=True)  # User who liked


class Rebleat(db.Model):
    __tablename__ = "Rebleat"
    bleat_id = db.Column(db.Integer, db.ForeignKey(
        Bleat.id, ondelete='CASCADE'), nullable=False, primary_key=True)  # Bleat rebleat
    rebleater_id = db.Column(db.Integer, db.ForeignKey(
        User.id, ondelete='CASCADE'), nullable=False, primary_key=True)  # User who rebleated


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
        db.session.add(new_user)
        # commit to the database
        db.session.commit()
    return "success"


def generate_bleat(n=400):
    size = len(User.query.all())
    for i in range(n):
        author_id = random.randint(1, size - 1)
        if User.query.filter_by(id=author_id).first():
            content = lorem.words(10)
            title = lorem.words(1)
            like = 0
            retweet = 0
            reply = 0  # Pour l'instant c'est juste un compteur, on en fera une liste de reponse
            date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_bleat = Bleat(title=title, content=content, author_id=author_id,
                              like=like, retweet=retweet, reply=reply, date=date)
            db.session.add(new_bleat)
            db.session.commit()
    return "success"


def generate_relationship(n=1000):
    size = len(User.query.all())
    for i in range(n):
        id1, id2 = random.randint(1, size-1), random.randint(1, size-1)
        if id1 != id2:
            if not (db.session.query(Relationship).filter(and_(Relationship.userID1 == id1, Relationship.userID2 == id2)).first() or db.session.query(Relationship).filter(and_(Relationship.userID1 == id2, Relationship.userID2 == id1)).first()):

                p = bool(random.randint(0, 1))
                date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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


def generate_likes_and_rebleat(n=1000):
    size_user = len(User.query.all())
    size_bleat = len(Bleat.query.all())
    for i in range(n):
        id_user, id_bleat = random.randint(
            1, size_user-1), random.randint(1, size_bleat-1)
        if not db.session.query(Bleat).filter(and_(Bleat.author_id == id_user, Bleat.id == id_bleat)).first():
            if not db.session.query(Like).filter(and_(Like.bleat_id == id_bleat, Like.liker_id == id_user)).first():
                # the user like the post
                db.session.query(Bleat).filter_by(
                    id=id_bleat).update({'like': Bleat.like + 1})
                db.session.add(Like(bleat_id=id_bleat, liker_id=id_user))

        id_user, id_bleat = random.randint(
            1, size_user-1), random.randint(1, size_bleat-1)
        if not db.session.query(Bleat).filter(and_(Bleat.author_id == id_user, Bleat.id == id_bleat)).first():
            if not db.session.query(Rebleat).filter(and_(Rebleat.rebleater_id == id_user, Rebleat.bleat_id == id_bleat)).first():
                db.session.query(Bleat).filter_by(id=id_bleat).update(
                    {'retweet': Bleat.retweet + 1})
                db.session.add(
                    Rebleat(bleat_id=id_bleat, rebleater_id=id_user))
        db.session.commit()

    return "success"


def question_4():
    r_table = Relationship.query.all()
    r_count = Relationship.query.filter_by(pending=True).count()
    follow_relationship = []
    for r in r_table:
        follow_relationship.append((r.userID1, r.userID2))

    temp = set(follow_relationship) & {(b, a) for a, b in follow_relationship}
    """ consider only one tuple per each symetric relationships """
    res = {(a, b) for a, b in temp if a < b}
    return res


def question_5(user_id):
    graph_rel = nx.DiGraph()
    r_waiting = Relationship.query.filter_by(pending=False)
    for r in r_waiting:
        graph_rel.add_edge(r.userID1, r.userID2)

    s = set()
    for p in graph_rel.predecessors(user_id):
        for pp in graph_rel.predecessors(p):
            s.add(pp)
    return s


if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    # print(generate_users())
    # print(generate_bleat())
    # print(generate_relationship())
    # print(generate_likes_and_rebleat())

    print(question_5(36))
