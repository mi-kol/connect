from flask import Flask, render_template, request, redirect, g, session
from flask_socketio import SocketIO, emit
from flask_wtf import FlaskForm
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired
import os
import psycopg2
import sys

import eventlet
eventlet.monkey_patch()


app = Flask(__name__)
app.config['SECRET_KEY'] = 'ZLiqlknGV3MfIXyD'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://doadmin:qpj8u2fqgf2h1woz@menno-connect-db-do-user-3819703-0.db.ondigitalocean.com:25060/defaultdb?sslmode=require'

socketio = SocketIO(app, async_mode='eventlet')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    firstname = db.Column(db.String(24), nullable=False)
    lastname = db.Column(db.String(36), nullable=False)
    email = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(300), nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username 

class Post(db.Model):
    __tablename__ = 'post'
    post_id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    timestamp = db.Column(db.TIMESTAMP)
    content = db.Column(db.Text)
    title = db.Column(db.Text)

    def __repr__(self):
        return '<Post: %r>' % self.content

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = User.query.filter(User.user_id == user_id).first()

@app.route('/')
def index():
    print(session.get('user_id'))
    pureposts = Post.query.all()
    posts = []
    if session.get('user_id') is None:
        return redirect('/auth')
    for post in pureposts:
        author = User.query.filter(User.user_id == post.author_id).first()
        posts.append({"title": post.title, "content": post.content, "author": author.username})
    return render_template('feed.html', posts=posts)

@app.route('/auth', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        print("[INFO] Received POST request from '/'.", file=sys.stderr)
        handle = request.form['username']
        password = request.form['password']
        reqType = request.form['type']
        if reqType == 'register' and handle and password:
            firstname = request.form['firstname']
            lastname = request.form['lastname']
            email = request.form['email']
            newUser = User(username=handle,
                           email=email,
                           firstname=firstname,
                           lastname=lastname,
                           password=password
                           )
            db.session.add(newUser)
            db.session.commit()
            session['user_id'] = newUser.user_id
            return redirect('/')
        else:
            if handle and password:
                existing_user = User.query.filter(User.username == handle).first()
                if existing_user:
                    session['user_id'] = existing_user.user_id
                    return redirect('/')
                else:
                    existing_user = User.query.filter(User.email == handle).first()
                    if existing_user:
                        session['user_id'] = existing_user.user_id
                        return 'logged in'
                    return redirect('/')
    else:    
        return render_template('splash.html')

@app.route('/posts')
def posts():
    return Post.query.first().content

@app.route('/wipeposts')
def wipeposts():
    Post.query.delete()
    db.session.commit()
    return "Posts deleted."

@app.route('/new', methods=['GET', 'POST'])
def new():
    if request.method == 'POST':
        print("[INFO] Received POST post from '/'.", file=sys.stderr)
        title = request.form['title']
        body = request.form['text']
        user = session.get('user_id')
        newPost = Post(author_id=user,
                       content=body,
                       title=title)
        db.session.add(newPost)
        db.session.commit()
        return redirect('/')
    else:
        if session.get('user_id') is None:
            return redirect('/auth')
        return render_template('new.html')

if __name__ == "__main__":
    socketio.run(app, debug=True, host='0.0.0.0', port=80)
