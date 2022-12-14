from collections import deque
import os
import matplotlib.pyplot as plt
from sqlalchemy import update
import numpy as np
import scipy as sp
from data_struct import LinkedList
from sqlite3 import Connection as SQLite3Connection
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   url_for, g, session, send_file)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import PrimaryKeyConstraint, CheckConstraint, UniqueConstraint
from sqlalchemy import event
from sqlalchemy.engine import Engine
import datetime
import hashlib
from data_struct import *
import networkx as nx
import random
from collections import Counter
from Levenshtein import distance
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
    email = db.Column(db.String(64), unique=True)
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


@app.route("/")  # Home root
def home():
    current_user = User.query.filter_by(id=session.get("current_user")).first()

    if current_user:
        return render_template("Bleatter.html", name=current_user.username)
    else:
        return render_template("Bleatter.html")


@app.route("/user", methods=["POST"])  # create user
def create_user():
    data = request.get_json()
    new_user = User(username=data["username"],
                    email=data["email"],
                    location=data["location"],
                    pwd=hash_password(data["password"])
                    )
    # add the user to the database
    db.session.add(new_user)
    # commit to the database
    db.session.commit()  # take the entire session and update the database.
    return jsonify({"message": "User created"}), 200


@app.route("/users/<int:ID>", methods=["GET", "POST", "DELETE"])
def users(ID):

    if (request.method == "GET"):
        user = User.query.filter_by(id=ID).first()
        if user:
            return jsonify(user.serialize()), 200
        else:
            return jsonify({"message": " No student found"}), 201

    elif (request.method == "POST"):
        data = request.get_json()
        new_user = User(username=data["username"],
                        email=data["email"],
                        location=data["location"],
                        pwd=hash_password(data["password"])
                        )
        # add the user to the database
        db.session.add(new_user)
        # commit to the database
        db.session.commit()  # take the entire session and update the database.
        return jsonify({"message": "User created"}), 200
    else:
        user_del = User.query.filter_by(id=ID).first()
        if user_del:
            db.session.delete(user_del)
            db.session.commit()
            return jsonify({"message": "User " + str(ID) + " and his associated bleats have been successfully deleted"}), 200
        else:
            return jsonify({"message": "user not found"}), 201


@app.route("/bleat", methods=["POST"])
def create_bleat():
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "missing data, please enter it in the body"}), 400

        for field in ["title", "content", "author_id", "like", "retweet", "reply"]:
            if field not in data.keys():
                return jsonify({"error": "no " + field + " in data"}), 400

        user = User.query.filter_by(id=data["author_id"]).first()
        if user:
            new_bleat = Bleat(title=data["title"],
                              content=data["content"],
                              author_id=data["author_id"],
                              like=data["like"],
                              retweet=data["retweet"],
                              reply=data["reply"],
                              date=datetime.datetime.now()
                              )

            db.session.add(new_bleat)
            db.session.commit()
            return jsonify({"message": "Bleat created"}), 200
        else:
            return jsonify({"message": "User does not exist"}), 201

    except Exception as e:
        return jsonify({"error": "Failed, caught exception " + str(e)}), 400


def hash_password(pwd):
    # we use sha256 hashfunction to hash the password
    h = hashlib.sha256(str(pwd).encode('utf-8'))
    return str(int(h.hexdigest(), base=16))


@app.route("/bleat/<int:ID>", methods=["DELETE"])
def delete_a_bleat(ID):
    try:
        data = Bleat.query.all()
        T = HashTable(len(data))
        for i in range(len(data)):
            T.put(data[i].id, data[i])

        bleat_del = T.get(ID)
        if bleat_del is None:
            return jsonify({"message": "The Bleat with ID = " + str(ID) + " does not exist"}), 201
        else:
            db.session.delete(bleat_del)
            db.session.commit()
            return jsonify({"message": "The Bleat with ID = " + str(ID) + " as been successfully removed"}), 200
    except Exception as e:
        return jsonify({"error": "Failed, caught exception " + str(e)}), 400


@app.route("/signup", methods=["GET", "POST"])
def signup():
    # request.form is a kind of dictionnary
    if request.method == "GET":
        return render_template("signup.html")
    else:
        email = request.form["email"]
        username = request.form["username"]
        location = request.form["location"]
        pwd = request.form["password"]
        pwd_c = request.form["password_c"]

        if (pwd != pwd_c):
            flash("Passwords are different", "info")
            return redirect(url_for("signup"))

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists', "info")
            return redirect(url_for("signup"))
        else:
            new_user = User(email=email, username=username,
                            location=location, pwd=hash_password(pwd))
            db.session.add(new_user)
            db.session.commit()
            flash("Record was successfully added", "info")
            return render_template("signin.html"), 200


@app.route("/signin", methods=["GET", "POST"])
def signin():

    if request.method == "GET":
        return render_template("signin.html")

    else:
        email = request.form["email"]
        password = request.form["password"]  # Recuperation du form

    users = User.query.all()
    D = dict()  # Tuple email - user
    for i in range(len(users)):
        D[users[i].email] = users[i]  # tuple email - user

    if email in D.keys():
        user = D[email]  # Check if email exists
        # If yes check if this is the right password
        if hash_password(password) == user.pwd:
            # the session.current_user keep the id user of the current session
            session["current_user"] = user.id
            return redirect(url_for("home"))
        else:
            flash("Wrong password")
            return render_template("signin.html")
    else:
        flash("User does not exist")
        return render_template("signin.html")


@app.route("/logout")
def logout():
    session.pop("current_user", None)
    return redirect(url_for("home"))


@app.route("/post_a_bleat", methods=["GET", "POST"])
def post_a_bleat():
    if request.method == "GET":
        return render_template("post_a_bleat.html")
    else:
        if session.get('current_user') is None:
            return render_template("signin.html")
        else:
            id_user = session.get('current_user', None)
            if id_user is None:
                flash("Feature not available without connection", "info")
                return redirect(url_for("signin"))
            else:
                title = request.form["title"]
                content = request.form["content"]

                # get the user associated to the id
                user = User.query.filter_by(id=id_user).first()
                if not user:
                    flash("User with " + id_user + " does not exist")
                    return redirect(url_for("post_a_bleat"))
                else:
                    new_bleat = Bleat(title=title, content=content, author_id=int(
                        id_user), like=0, retweet=0, reply=0, date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

                    db.session.add(new_bleat)
                    db.session.commit()
                    flash("Message was successfully added", "info")
                    return redirect(url_for("profile"))


@app.route("/users", methods=["GET"])
def get_all_users():
    users = User.query.all()
    return jsonify([user.serialize() for user in users]), 200


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/home_page", methods=["GET", "POST"])
def home_user():
    g.search = "home_page"
    word_counter = Counter()
    bleats = Bleat.query.all()
    # Now find all bleat with the searched word inside
    d_search = dict()
    # Create the dict {word: linkedlist of all bleats containing word]}
    for bleat in bleats:
        for w in bleat.title.split():
            word_counter[w] += 1
            if not d_search.get(w):
                d_search[w] = LinkedList()  # Access O(n) Insertion O(1)
                d_search[w].insert_beginning(bleat)
            else:
                d_search[w].insert_beginning(bleat)

        for w in bleat.content.split():
            word_counter[w] += 1
            if not d_search.get(w):
                d_search[w] = LinkedList()
                d_search[w].insert_beginning(bleat)
            else:
                d_search[w].insert_beginning(bleat)
    most_used_word = [u for u in word_counter.most_common(20)]

    if request.method == "GET":

        # Recup friend's id list
        relation = Relationship.query.all()
        friends_id = []  # the ongoing friend id are store in this array

        user_id = session.get('current_user')

        for ele in relation:
            if ele.userID1 == user_id and ele.pending:
                friends_id.append(ele.userID2)

        users = User.query.all()
        friends_name = dict()
        while len(list(friends_name.keys())) != len(friends_id):
            for e in users:
                if e.id in friends_id:
                    friends_name[e.id] = e
        # friends_name dictionary with (user.id) : user

        # Recup friend's bleat

        friends_bleats = []

        for ele in bleats:
            if ele.author_id in friends_id:
                friends_bleats.append((friends_name[ele.author_id], ele))

        # Like_index Creation
        like_bd = Like.query.all()
        like_index = dict()

        for l in like_bd:  # For each user we have all the bleat the liked
            if like_index.get(l.liker_id):
                like_index[l.liker_id].append(l.bleat_id)
            else:
                like_index[l.liker_id] = [l.bleat_id]

        # Rebleat_index Creation
        rb_bd = Rebleat.query.all()
        rb_index = dict()

        for r in rb_bd:
            if rb_index.get(r.rebleater_id):
                rb_index[r.rebleater_id].append(r.bleat_id)
            else:
                rb_index[r.rebleater_id] = [r.bleat_id]

        # Add rebleat
        for f_id in friends_name.keys():
            if rb_index.get(f_id):
                for b in rb_index.get(f_id):
                    bl = Bleat.query.filter(Bleat.id == b).first()
                    author = User.query.filter(User.id == bl.author_id).first()
                    friends_bleats.append((author, bl))

        # Sort it from youngest to oldest
        friends_bleats = sorted(
            friends_bleats, key=lambda friends_bleats: friends_bleats[1].date)
        friends_bleats.reverse()

        return render_template("home_page.html", messages=friends_bleats, like_index=like_index,
                               rb_index=rb_index,
                               most_used_word=most_used_word,
                               current_user=session.get("current_user"))

    if request.method == "POST":

        # get the data from the form name "search"
        word = request.form["search"]
        user_index = {}
        # First find all profile with username same as searched word
        users = User.query.all()
        user_found = {}
        for ele in users:
            user_index[ele.id] = ele  # Create user_index

            if ele.username.lower() == word.lower():  # Search if word user exist
                user_found[ele] = str(ele.id)

        user_bool = False
        if len(user_found.keys()) > 0:
            user_bool = True

        # if the word is well written and found it return the list of bleats containing the word
        if d_search.get(word):
            bleat_found = d_search[word]
        else:
            # otherwise, the list of bleats containing a word near to the searched word (by Levenstein distance)
            # is return
            bleat_found = LinkedList()

            for w in d_search.keys():
                if abs(len(w) - len(word)) < 3:
                    if distance(w, word) <= 2:  # compute the Levenshtein distance between 2 words
                        if bleat_found.head == None:
                            bleat_found.head = d_search[w].head
                        else:
                            bleat_found = LinkedList.concatenate(
                                bleat_found, d_search[w])

        bleat_found = bleat_found.to_list()
        bleat_found = sorted(
            bleat_found, key=lambda ele: ele.date)
        bleat_found.reverse()

        return render_template("search.html", user_bool=user_bool, word_s=word, user_found=user_found, b_list=bleat_found, user_index=user_index)


"""function to get the friends of a given user"""


@app.route("/api/user/<int:ID>/friends", methods=["GET"])
def friends_of(ID):
    users = User.query.all()  # load the users in the memory
    friends = Relationship.query.all()  # load all the relationship data in the memory
    # implement a hash function with direct chaining to store the relation ship

    T = HashTable(len(users))
    for i in range(len(users)):
        T.put(users[i].id, users[i])

    r = dict()  # r is a hashmap of linkedList
    for ele in friends:
        if ele.pending is True:  # pending = True : relation / pending = 0 : not yet
            f = {
                "id": T[ele.userID2].id,
                "username": T[ele.userID2].username,
                "email": T[ele.userID2].email,
                "location": T[ele.userID2].location
            }

            if not(ele.userID1 in r.keys()):
                r[ele.userID1] = LinkedList()
                r[ele.userID1].insert_at_end(f)
            else:
                r[ele.userID1].insert_at_end(f)

    return r[ID].to_list()


""" fonction showing friends and pending invitation   """
""" To do that we use a sparse matrix to store a digraph of relationships between users """
""" more users there are in the database sparser the matrix relation will be, so we use this special datastructure
to gain storage space and computing time"""


@app.route("/user/friends", methods=["GET"])
def show_friends():
    user_id = session.get('current_user')
    g.search = False
    if user_id is None:
        return render_template("signin.html")
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

    name = U[user_id]["username"]

    G_p = nx.DiGraph()
    G_np = nx.DiGraph()

    for r in relationships:
        if r.pending == True:
            G_p.add_edge(r.userID1, r.userID2)
        else:
            G_np.add_edge(r.userID1, r.userID2)

    F, I, W = [], dict(), dict()

    if user_id in G_p:
        for f in G_p.successors(user_id):  # friends of current user
            F.append(U[f])
    if user_id in G_np:
        for i in G_np.successors(user_id):  # current user invite these user
            I[i] = U[i]
        # want to be friend with current user
        for w in G_np.predecessors(user_id):
            W[w] = U[w]

    FF = dict()
    # BFS from the user_id node to the leaf of a bfs tree of depth 2
    if user_id in G_p:
        T = nx.descendants_at_distance(G_p, user_id, distance=2)
    else:
        T = list(G_p.nodes)
        T_temp = []
        randomlist = random.sample(range(0, len(T)), 10)
        for i in randomlist:
            T_temp.append(T[i])
        T = T_temp
        # random friend suggestion

    for ff in T:
        if not (ff == user_id or ff in I.keys() or ff in W.keys() or ff in FF.keys()):
            FF[ff] = U[ff]

    return render_template("friends.html", name=name, F=F, I=list(I.values()), W=list(W.values()), FF=list(FF.values()))


@ app.route("/bleats/<word>", methods=["GET"])
def find_bleat_word(word):
    # get the bleat
    users = User.query.all()
    d = dict()
    for i in range(len(users)):
        d[users[i].id] = users[i].username

    bleats = Bleat.query.all()
    bleat_ll = LinkedList()
    for b in bleats:
        bl = {"title": b.title,
              "content": b.content,
              "author": d[int(b.author_id)],
              "like":  b.like,
              "retweet": b.retweet,
              "reply": b.reply,
              "date": b.date
              }
        bleat_ll.insert_beginning(bl)

    temp = bleat_ll.head  # start a the head of the linkedList
    prev = None

    while (temp != None and temp.data["content"].find(word + " ") == -1):
        head_ref = temp.next_node
        temp = head_ref

    while (temp != None):  # programming a remove function under condition
        while (temp != None and temp.data["content"].find(word + " ") != -1):
            prev = temp
            temp = temp.next_node

        if (temp == None):
            break

        prev.next_node = temp.next_node
        temp = prev.next_node

    bleat_ll.head = head_ref  # this the head of the linked list
    b_list = bleat_ll.to_list()
    return render_template("show_bleats.html", b_list=b_list)


@ app.route("/user/friends/<int:id>", methods=["GET", "POST"])
def accept_friends(id):
    if request.method == "GET":
        redirect(url_for("show_friends"))
    else:
        user_id = session.get('current_user')
        if user_id is None:
            return render_template("signin.html")
        else:
            rela = Relationship.query.filter(
                (Relationship.userID1 == int(user_id)) & (Relationship.userID2 == id)).first()
            if rela:
                flash("Error : Relationship already exists", "error")
                return redirect(url_for("show_friends"))
            else:
                db.session.query(Relationship).filter((Relationship.userID1 == id) & (
                    Relationship.userID2 == user_id)).update({'pending': True})

                db.session.add(Relationship(userID1=int(user_id), userID2=id,
                                            date=datetime.datetime.now(), pending=True))
                db.session.commit()
                return redirect(url_for("show_friends"))


@ app.route("/user/friend_request/<int:id>", methods=["GET", "POST"])
def friend_request(id):
    if request.method == "GET":
        return redirect(url_for("show_friends"))
    else:
        user_id = session.get('current_user')
        if user_id is None:
            return render_template("signin.html")
        else:
            rela = Relationship.query.filter(
                (Relationship.userID1 == int(user_id)) & (Relationship.userID2 == id)).first()
            if rela:
                flash("Error : Relationship already exists", "error")
                return redirect(url_for("show_friends"))
            else:
                db.session.add(Relationship(userID1=int(user_id), userID2=id,
                                            date=datetime.datetime.now(), pending=False))
                db.session.commit()
                return redirect(url_for("show_friends"))


@ app.route("/user/remove_friend/<int:ID>", methods=["POST"])
def remove_friend(ID):
    if request.method == "POST":
        user_id = session.get("current_user")
        if user_id is None:
            return render_template("signin.html")
        else:
            rela1 = Relationship.query.filter(
                (Relationship.userID1 == int(user_id)) & (Relationship.userID2 == ID)).first()
            rela2 = Relationship.query.filter(
                (Relationship.userID1 == ID) & (Relationship.userID2 == int(user_id))).first()
            print(rela1)
            print(rela2)
            if rela1 and rela2:
                db.session.delete(rela1)
                db.session.delete(rela2)
                db.session.commit()
            return redirect(url_for("show_friends"))


@ app.route("/my_profile", methods=["GET", "POST"])
def profile():
    g.search = "profile"  # give the possibility of searching a word or a use in the nav bar
    if request.method == "GET":
        cur_id = session.get("current_user")
        users = User.query.all()

        nb_friends = Relationship.query.filter(
            (Relationship.userID1 == cur_id) & (Relationship.pending == True)).count()

        current_user = User.query.filter_by(id=cur_id).first()
        # current_user = session["user_index"].get(cur_id)
        # use the foreign key bleats.author to User and get all his bleats
        bleats = current_user.bleats

        messages = LinkedList()

        for b in bleats:
            messages.insert_at_end(b)

        # Add rebleat
        rebleat = Rebleat.query.all()

        for rb in rebleat:
            if rb.rebleater_id == cur_id:
                bleat = Bleat.query.filter_by(id=rb.bleat_id).first()
                messages.insert_at_end(bleat)

        messages = messages.to_list()
        messages = sorted(messages, key=lambda messages: messages.date)[::-1]

        return render_template("profile.html", my_account=True, email=current_user.email, nb_friends=nb_friends, id=current_user.id,
                               username=current_user.username, location=current_user.location, messages=messages)

    if request.method == "POST":
        # search function only for your own bleats or your friends
        # get the data from the form name "search"
        word = request.form["search"]
        cur_id = session.get("current_user")
        friend_index = dict()
        relationship__current_user = Relationship.query.filter(
            (Relationship.userID1 == cur_id) & (Relationship.pending == True))

        # First find all profile with username same as searched word
        users = User.query.all()
        user_found = {}
        users_dict = dict()
        for u in users:
            users_dict[u.id] = u

        for ele in relationship__current_user:
            friend_index[ele.userID2] = users_dict[ele.userID2]
            if users_dict[ele.userID2].username.lower() == word.lower():
                path = "/profile/" + str(ele.userID2)
                user_found[ele] = path

        user_bool = False
        if len(user_found.keys()) > 0:
            user_bool = True

        # Now find all bleat with the searched word inside
        d_search = dict()
        bleats = Bleat.query.all()

        # Create the dict {word: linkedlist of all bleats containing word]}
        for bleat in bleats:
            if bleat.author_id in friend_index.keys():
                # take the title into account
                for w in bleat.title.split():
                    if not d_search.get(w):
                        d_search[w] = LinkedList()
                        d_search[w].insert_at_end(bleat)
                    else:
                        d_search[w].insert_at_end(bleat)

                # take the content into account
                for w in bleat.content.split():

                    if not d_search.get(w):
                        d_search[w] = LinkedList()
                        d_search[w].insert_at_end(bleat)
                    else:
                        d_search[w].insert_at_end(bleat)

        # get it in O(1) all bleat
        if d_search.get(word):
            # transform our linkedList to list
            bleat_found = d_search[word].to_list()
            w = word
        else:
            bleat_found = []

        # Find your friends
        users = User.query.all()
        user_index = {}
        user_found = {}
        for ele in users:
            user_index[ele.id] = ele  # Create user_index

            if ele.username.lower() == word.lower():  # Search if word user exist
                user_found[ele] = str(ele.id)

        return render_template("search.html", user_bool=user_bool, word_s=w, user_found=user_found, b_list=bleat_found, user_index=friend_index)


@app.route("/profile/<int:ID>", methods=["GET"])
def profile_user(ID):
    if request.method == "GET":
        users = User.query.all()

        user_searched = User.query.filter_by(id=ID).first()

        rel_list = dict()
        for rel in Relationship.query.all():
            if not rel.userID1 in rel_list.keys():
                rel_list[rel.userID1] = dict()
                rel_list[rel.userID1][True] = set()
                rel_list[rel.userID1][False] = set()
            else:
                rel_list[rel.userID1][rel.pending].add(rel.userID2)

        nb_friends = len(rel_list[ID][True])

        # What about the relationship between this user and the current user ?
        id_cur = session.get("current_user")
        state = "F"
        if id_cur in rel_list[ID][True]:
            state = "Friend"
        elif (id_cur in rel_list[ID][False]):
            state = "He / She sent you a friend request"
        else:
            if ID in rel_list[id_cur][False]:
                state = "Friend request already sent"

        username = user_searched.username
        email = user_searched.email
        location = user_searched.location
        bleats = user_searched.bleats

        messages = LinkedList()

        for t in bleats:
            messages.insert_at_end(t)

        return render_template("profile.html", id=ID, my_account=False, email=email, nb_friends=nb_friends, username=username, location=location, messages=messages.to_list(), state=state)


@app.route("/user/remove_bleat/<int:ID>", methods=["POST"])
def delete_a_user_bleat(ID):

    if request.method == "POST":
        cur_id = session.get("current_user")
        current_user = User.query.filter_by(id=cur_id).first()

        bleat_removed = Bleat.query.filter(
            (Bleat.author_id == cur_id) & (Bleat.id == ID)).first()
        if bleat_removed is None:
            flash("You are not allowed to delete this bleat, you are not the original author, go to your Home Page and remove your rebleat from there")
            return redirect(url_for("profile"))
        else:
            flash("The Bleat entitled '" + bleat_removed.title +
                  "' has been successfully remove from Bleatter")
            db.session.delete(bleat_removed)
            db.session.commit()
            return redirect(url_for("profile"))


@app.route("/user/remove_user", methods=["POST"])
def delete_user():
    if request.method == "POST":
        cur_id = session.get("current_user")
        user = db.session.query(User).filter(User.id == cur_id).first()
        db.session.delete(user)
        db.session.commit()
        flash("Your account have been successfully deleted", "info")

        return redirect(url_for("logout"))


# Comme son nom l'indique c'est la zone de test
@app.route("/zone_test", methods=["GET"])
def test():
    return render_template("test_bootstrap.html")


@app.route("/like/<bleat_id>", methods=["POST", "DELETE"])
def like(bleat_id):
    if request.method == "POST":

        # Create the new like
        new_like = Like()
        new_like.bleat_id = bleat_id
        new_like.liker_id = session.get("current_user")

        # Add +1 to bleat.like
        bleat = db.session.query(Bleat).filter(Bleat.id == bleat_id).first()
        bleat.like += 1

        # Add the new like
        db.session.add(new_like)
        db.session.commit()
        return {}

    if request.method == "DELETE":

        # Recup like to delete
        like_toDelete = db.session.query(Like).filter(
            Like.bleat_id == bleat_id and Like.liker_id == session.get("current_user")).first()

        # Add -1 to bleat.like
        bleat = db.session.query(Bleat).filter(Bleat.id == bleat_id).first()
        if bleat.like > 0:
            bleat.like -= 1

        # Delete it
        db.session.delete(like_toDelete)
        db.session.commit()
        return {}


@app.route("/rebleat/<int:bleat_id>", methods=["POST", "DELETE"])
def rebleat(bleat_id):
    if request.method == "POST":

        # Create the new rebleat
        new_rebleat = Rebleat()
        new_rebleat.bleat_id = bleat_id
        new_rebleat.rebleater_id = session.get("current_user")

        # Add +1 to bleat.retweet
        bleat = db.session.query(Bleat).filter(Bleat.id == bleat_id).first()
        bleat.retweet += 1

        # Add the new rebleat
        db.session.add(new_rebleat)
        db.session.commit()
        return {}

    if request.method == "DELETE":

        # Recup like to delete
        rebleat_toDelete = db.session.query(Rebleat).filter(
            Rebleat.bleat_id == bleat_id and Rebleat.rebleater_id == session.get("current_user")).first()

        # Add -1 to bleat.like
        bleat = db.session.query(Bleat).filter(Bleat.id == bleat_id).first()
        if bleat.retweet > 0:
            bleat.retweet = bleat.retweet - 1

        # Delete it
        db.session.delete(rebleat_toDelete)
        db.session.commit()
        return {}


@app.route("/my_profile/<int:id_b>/<string:t>", methods=["GET"])
def develop_counters(id_b, t):
    if session.get("current_user"):
        users = User.query.all()
        d = dict()
        for u in users:
            d[u.id] = u

        output = LinkedList()
        if t == "rebleat":
            rebleats = Rebleat.query.filter_by(bleat_id=id_b)
            req = "They shared your Bleat"
            for r in rebleats:
                output.insert_beginning(d[r.rebleater_id])
        if t == "like":
            likes = Like.query.filter_by(bleat_id=id_b)
            req = "They loved your Bleat"
            for l in likes:
                output.insert_beginning(d[l.liker_id])
        if t == "reply":
            req = "They replied to your Bleat"
            pass
        return render_template("fans.html", request=req, response=[user.serialize() for user in output.to_list()])
    else:
        return render_template("404_template.html")


if __name__ == "__main__":

    with app.app_context():
        db.create_all()
    app.debug = True
    app.env = "development"
    app.run(host="localhost", port="5000")
