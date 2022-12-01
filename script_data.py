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
import networkx as nx
import matplotlib.pyplot as plt
from sqlalchemy import PrimaryKeyConstraint, CheckConstraint


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
    # Pour l'instant c'est juste un compteur, on en fera une liste de reponse
    reply = db.Column(db.Integer)
    date = db.Column(db.String(256))

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
            date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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


def show_friends():

    users = User.query.all()  # load the users in the memory
    # load all the relationship data in the memory
    relationships = Relationship.query.all()
    # implement a hash function with direct chaining to store the relation ship

    # hash map storing all users accessible by their id
    U = dict()
    for u in users:
        U[u.id] = {"id": u.id,
                   "username": u.username,
                   "email": u.email,
                   "location": u.location}

    G_p = nx.DiGraph()
    G_np = nx.DiGraph()

    for r in relationships:
        if r.pending == True:
            G_p.add_edge(r.userID1, r.userID2)
        else:
            G_np.add_edge(r.userID1, r.userID2)

    # pos = nx.spring_layout(G,seed=63)
    # nx.draw(G, pos=nx.random_layout(G, seed=64), arrows=True, with_labels=True)
    # nx.draw_networkx_edge_labels(
        # G, pos = nx.random_layout(G, seed=64), edge_labels = edge_lab)
    # plt.savefig("static/graph.png", format="PNG")

    return G_p, G_np


if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    # print(generate_users())
    # print(generate_bleat())
    # print(generate_relationship())
    G_p, G_np = show_friends()
    nx.draw(G_p, pos=nx.random_layout(G_p, seed=64), with_labels=True)
    plt.show()
    nx.draw(G_np, pos=nx.random_layout(G_np, seed=64), with_labels=True)
    plt.show()
