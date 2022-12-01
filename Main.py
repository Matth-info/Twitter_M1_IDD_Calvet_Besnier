from sqlalchemy import update
import numpy as np
from scipy.sparse import csr_matrix
import scipy as sp
from data_struct import LinkedList
from sqlite3 import Connection as SQLite3Connection
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   url_for, g, session)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import PrimaryKeyConstraint, CheckConstraint, UniqueConstraint
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


@app.route("/")  # testing root
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
    db.session.commit()  # take the entire session and update the
    # database.
    return jsonify({"message": "User created"}), 200


@app.route("/users/<int:ID>", methods=["GET", "POST", "DELETE"])
def users(ID):
    # users = User.query.all()

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
        db.session.commit()  # take the entire session and update the
        # database.
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
                        id_user), like=0, retweet=0, reply=0, date=datetime.datetime.now())

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

    if request.method == "GET":

        # Recup friend's id list
        relation = Relationship.query.all()
        friend_id = []

        user_id = session.get('current_user')

        for ele in relation:
            if ele.userID1 == user_id and ele.pending:
                friend_id.append(ele.userID2)

        # Recup friend's bleat
        bleats = Bleat.query.all()
        friend_bleats = []

        for ele in bleats:
            if ele.author_id in friend_id:
                friend_bleats.append(ele)

        # Sort it from youngest to oldest
        sorted(friend_bleats, key=lambda friend_bleats: friend_bleats.date)
        friend_bleats.reverse()

        message = []
        name = []
        date = []
        like = []
        rebleat = []
        reply = []

        for t in friend_bleats:
            name.append(User.query.filter_by(id=t.author_id).first().username)
            message.append(t.title + " : " + t.content)
            date.append(t.date[0:10] + " at  " + t.date[11:19])
            like.append(t.like)
            rebleat.append(t.retweet)
            reply.append(t.reply)

        return render_template("home_page.html", len=len(message), message=message, name=name, date=date, like=like, rebleat=rebleat, reply=reply)

    if request.method == "POST":  # Method = POST

        word = request.form["search"]  # get the data from the form name search
        user_index = {}

        # First find all profile with username same as searched word
        users = User.query.all()
        user_found = {}
        for ele in users:
            user_index[ele.id] = ele  # Create user_index

            if ele.username.lower() == word.lower():  # Search if word user exist
                path = '/profile/' + str(ele.id)
                user_found[ele] = path

        # Now find all bleat with the searched word inside
        d_search = dict()
        bleats = Bleat.query.all()

        # Create the dict {word: linkedlist of all bleats containing word]}
        for bleat in bleats:
            for w in bleat.content.split():
                if not d_search.get(w):
                    d_search[w] = LinkedList()
                    d_search[w].insert_at_end(bleat)
                else:
                    d_search[w].insert_at_end(bleat)

        # Recup in O(1) all bleat
        if d_search.get(word):
            # transform our linkedList to list
            bleat_found = d_search[word].to_list()
        else:
            bleat_found = []

        return render_template("search.html", user_found=user_found, b_list=bleat_found, user_index=user_index)


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
    if user_id is None:
        return render_template("signin.html")
    users = User.query.all()  # load the users in the memory
    friends = Relationship.query.all()  # load all the relationship data in the memory
    # implement a hash function with direct chaining to store the relation ship

    # hash map storing all users accessible by their id
    U = dict()
    for u in users:
        U[u.id] = {"id": u.id,
                   "username": u.username,
                   "email": u.email,
                   "location": u.location}

    name = U[user_id]["username"]
    if len(friends) == 0:
        return render_template("friends.html", name=name)
    coord_1 = np.array([])
    coord_2 = np.array([])
    data = np.array([], dtype=np.int8)
    for rel in friends:
        coord_1 = np.append(coord_1, int(rel.userID1))
        coord_2 = np.append(coord_2, int(rel.userID2))
        if rel.pending == False:
            data = np.append(data, 1)
        else:
            data = np.append(data, 2)
    # create a sparse matrix that stores the relationships
    Rel_sparse_mat = sp.sparse.coo_matrix(
        (data, (coord_1, coord_2)), shape=(len(U), len(U)))
    # add missing zeros
    r = Rel_sparse_mat.todense()

    # the row represents friends of the current user
    friends_of_user = r[user_id]
    # the column represents who is friends or want to be friend with the current user
    future_friends_of_user = r[:, user_id].T

    F, I, W = [], dict(), dict()
    # using dictionary help to avoid dealing with dublicates
    for i in range(len(U)):

        if friends_of_user[0, i] == 2:  # friends
            F.append(U[i])
        if friends_of_user[0, i] == 1:  # current user invite him
            I[U[i]["id"]] = U[i]
        # want to be friend with current user
        if future_friends_of_user[0, i] == 1:
            W[U[i]["id"]] = U[i]

    # using a dictionary (duplicate are not allowed) to avoid putting 2 times the friend of friend of the current user
    # set are not usable here because it needs unmutable object which is not the case for a dictionary

    FF = dict()
    for f in F:
        for ff in friends_of(f["id"]):  # list of dictionaries
            if not (ff["id"] == user_id or ff["id"] in FF.keys() or ff["id"] in I.keys() or ff["id"] in W.keys()):
                FF[ff["id"]] = ff

    return render_template("friends.html", name=name, F=F, I=list(I.values()), W=list(W.values()), FF=list(FF.values()))


@app.route("/bleats/<word>", methods=["GET"])
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


@app.route("/user/friends/<int:id>", methods=["GET", "POST"])
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


@app.route("/user/friend_request/<int:id>", methods=["GET", "POST"])
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


@app.route("/user/remove_friend/<int:ID>", methods=["POST"])
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


@app.route("/my_profile", methods=["GET"])
def profile():
    if request.method == "GET":
        cur_id = session.get("current_user")
        users = User.query.all()

        nb_friends = Relationship.query.filter(
            (Relationship.userID1 == cur_id) & (Relationship.pending == True)).count()

        current_user = User.query.filter_by(id=cur_id).first()
        # current_user = session["user_index"].get(cur_id)
        bleats = current_user.bleats  # use the foreign key bleats.author to User
        # get all his bleats

        messages = LinkedList()

        for b in bleats:
            messages.insert_at_end(b)

        return render_template("profile.html", email=current_user.email, nb_friends=nb_friends, username=current_user.username, location=current_user.location, messages=messages.to_list()[::-1])


@app.route("/profile/<int:ID>", methods=["GET"])
def profile_user(ID):
    if request.method == "GET":
        users = User.query.all()

        user_searched = User.query.filter_by(id=ID).first()
        # user_searched = session["user_index"].get(ID)
        username = user_searched.username
        location = user_searched.location
        bleats = user_searched.bleats

        messages = LinkedList()

        for t in bleats:
            messages.insert_at_end(t)

        return render_template("profile.html", len=len(messages.to_list()), username=username, location=location, message=messages.to_list())


@app.route("/user/remove_bleat/<int:ID>", methods=["POST"])
def delete_a_user_bleat(ID):

    if request.method == "POST":
        cur_id = session.get("current_user")
        current_user = User.query.filter_by(id=cur_id).first()

        bleat_removed = Bleat.query.filter(
            (Bleat.author_id == cur_id) & (Bleat.id == ID)).first()
        if bleat_removed is None:
            flash("You are not allowed to delete this bleat or it does not exist")
            return redirect(url_for("profile"))
        else:
            flash("The Bleat entitled " + bleat_removed.title +
                  " has been successfully remove from Bleatter")
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


if __name__ == "__main__":

    with app.app_context():
        db.create_all()
    app.debug = True
    app.env = "development"
    app.run(host="localhost", port="5000")
