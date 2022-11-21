from sqlite3 import Connection as SQLite3Connection
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   url_for, g, session)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import PrimaryKeyConstraint, CheckConstraint
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
    bleats = db.relationship("Bleat",cascade="all, delete")

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

class Relationship(db.Model):
    __tablename__ = "Relationship"
    id = db.Column(db.Integer, primary_key=True)
    userID1 = db.Column(db.Integer, db.ForeignKey("User.id"), nullable=False)
    userID2 = db.Column(db.Integer, db.ForeignKey("User.id"), nullable=False)
    CheckConstraint("userID1 != userID2", name="check1")
    date = db.Column(db.String(256))
    pending = db.Column(db.Boolean)


@app.route("/") # testing root 
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
    #users = User.query.all()

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
            return jsonify({"message": "User " + str(ID) + " and his associated bleats have been successfully deleted"}) , 200
        else:
            return jsonify({"message": "user not found"}), 201

@app.route("/bleat", methods=["POST"])
def create_bleat():
    try :
        data = request.get_json()
        if data is None:
            return jsonify({"error":"missing data, please enter it in the body"}),400

        for field in ["title", "content", "author_id","like","retweet","reply"]:
            if field not in data.keys():
                return jsonify({"error": "no " + field + " in data" }), 400

        user = User.query.filter_by(id = data["author_id"]).first()
        if user:
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
        else :
            return jsonify({"message" : "User does not exist"}), 201


    except Exception as e:
        return jsonify({"error" : "Failed, caught exception " + str(e)}), 400

def hash_password(pwd):
    # we use sha256 hashfunction to hash the password
    h = hashlib.sha256(str(pwd).encode('utf-8'))
    return str(int(h.hexdigest(), base=16))

@app.route("/bleat/<int:ID>",methods=["DELETE"])
def delete_a_bleat(ID):
    try :
        data = Bleat.query.all()
        T = HashTable(len(data))
        for i in range(len(data)):
            T.put(data[i].id,data[i])

        bleat_del = T.get(ID)
        if bleat_del is None:
            return jsonify({"message":"The Bleat with ID = " + str(ID) + " does not exist"}), 201
        else :
            db.session.delete(bleat_del)
            db.session.commit()
            return jsonify({"message":"The Bleat with ID = " + str(ID) + " as been successfully removed"}), 200
    except Exception as e:
        return jsonify({"error" : "Failed, caught exception " + str(e)}), 400


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
        flash("User does not exist")
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
        if session.get('current_user') is None:
            return render_template("signin.html")
        else :
            id_user = session.get('current_user',None)
            if id_user is None:
                flash("Feature not available without connection","info")
                return redirect(url_for("signin"))
            else:
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
            message.append(t.title +" : " + t.content)
            date.append(t.date[0:10] + " at  " + t.date[11:19])

        return render_template("home_page.html", len = len(message), message=message, name=name, date=date)


from data_struct import LinkedList

"""function to get the friends of a given user"""
@app.route("/user/<int:ID>/friends",methods=["GET"])
def friends_of(ID):
    users = User.query.all() # load the users in the memory
    friends = Relationship.query.all() # load all the relationship data in the memory
    # implement a hash function with direct chaining to store the relation ship

    T  = HashTable(len(users))
    for i in range(len(users)):
        T.put(users[i].id,users[i])

    r = dict() # r is a hashmap of linkedList
    for ele in friends:
        if ele.pending is True: # pending = True : relation / pending = 0 : not yet
            f = {
                    "id" : T[ele.userID2].id,
                    "username" : T[ele.userID2].username,
                    "email" : T[ele.userID2].email,
                    "location" : T[ele.userID2].location
            }

            if not(ele.userID1 in r.keys()):
                r[ele.userID1] = LinkedList()
                r[ele.userID1].insert_at_end(f)
            else:
                r[ele.userID1].insert_at_end(f)


    return jsonify(r[ID].to_list()), 200

@app.route("/bleats/<word>",methods=["GET"])
def find_bleat_word(word):
    # get the bleat
    users = User.query.all()
    d = dict()
    for i in range(len(users)):
        d[users[i].id] = users[i].username

    bleats = Bleat.query.all()
    bleat_ll = LinkedList()
    for b in bleats:
        bl = { "title": b.title,
            "content" : b.content,
            "author" : d[int(b.author_id)],
            "like" :  b.like,
            "retweet" : b.retweet,
            "reply" : b.reply,
            "date" : b.date
         }
        bleat_ll.insert_beginning(bl)

    temp = bleat_ll.head # start a the head of the linkedList
    prev = None

    while (temp != None and temp.data["content"].find(word + " ") == -1):
        head_ref = temp.next_node
        temp = head_ref

    while (temp != None): # programming a remove function under condition
        while (temp != None and temp.data["content"].find(word + " ") != -1):
            prev = temp
            temp = temp.next_node

        if (temp == None):
            break

        prev.next_node = temp.next_node
        temp = prev.next_node

    bleat_ll.head = head_ref # this the head of the linked list
    b_list = bleat_ll.to_list()
    return render_template("show_bleats.html", b_list = b_list)

@app.route("/profile", methods=["GET"])
def profile():
    if request.method == "GET":
        cur_id = session.get("current_user")
        users = User.query.all()

        current_user = User.query.filter_by(id = cur_id).first()
        username = current_user.username
        location = current_user.location
        bleats = current_user.bleats

        message = []
        date = []

        for t in bleats:
            message.append(t.title +" : " + t.content)
            date.append(t.date[0:10] + " at  " + t.date[11:19])


        return render_template("profile.html", len=len(message), username = username, location=location, message = message, date=date)


if __name__ == "__main__":

    with app.app_context():
        db.create_all()
    app.debug = True 
    app.env = "development"
    app.run(host="localhost", port="5000")
