import os,requests

from flask import Flask, session,render_template,request,redirect,url_for,jsonify
from flask_session import Session
from sqlalchemy import create_engine,exc
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_sqlalchemy import SQLAlchemy

 
app = Flask(__name__)

app.secret_key = 'fjewi32e3e287hde0/r*3f2-.,-32oefhew11-+ewf3''90'

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
   return render_template("firstpage.html") 

@app.route("/login", methods = ["GET","POST"])
def login():
   if request.method == 'GET' and session.get('username') is None:
      return render_template("login.html")
   elif request.method == 'GET' and session.get('username') != None:
      return redirect('/main')
   else:
      session['username'] = request.form.get('username')
      user = db.execute("SELECT * FROM account WHERE username = :username",{"username" : session['username']}).first()
      if user.password == request.form.get('password'):
         session['user_id'] = user.id
         return redirect('/main')
      else:
         session.pop('username',None)
         session.clear()
         return render_template("login.html",message="Username or password incorrect")

@app.route("/signup" , methods = ["GET","POST"])
def signup():
   message=""
   session.pop('username', None)
   session.pop('user_id', None)
   session.clear()
   if request.method == 'POST':
      session.pop('username', None)
      session.pop('user_id', None)
      session.clear()
      name = request.form.get('name')
      surname = request.form.get('surname')
      username = request.form.get('username')
      password = request.form.get('password')
      password_hash = generate_password_hash(password)
      try:
         db.execute("INSERT INTO account (name,surname,username,password) VALUES (:name, :surname, :username, :password)",{"name":name , "surname":surname , "username":username , "password": password})
      except exc.IntegrityError:
         db.rollback()
         message="Username is taken"
         return render_template("signup.html",message=message)
      
      db.commit()
      user = db.execute("SELECT * FROM account WHERE username = :username",{"username" : username}).first()
      session['username'] = user.username
      session['user_id'] = user.id
      session.modified = True
      return redirect('/main')
   else:
      message=""
      return render_template("signup.html",message=message)

@app.route("/main",methods = ["GET","POST"])
def main():
   try:
      results=" "
      message=""
      if session.get('username') != None:
         if request.method == 'POST':
            search_string = "%" + request.form.get('search') + "%"
            results = db.execute("SELECT * FROM books WHERE title ILIKE :search_string OR author ILIKE :search_string OR isbn ILIKE :search_string",{"search_string" : search_string}).fetchall()
            if results == [] : 
               message = "No books found"
            return render_template("main.html",user = "Logged in as " + session.get('username'),list=results,message = message)
         else:
            return render_template("main.html",user = "Logged in as " + session.get('username'))
      else:
         return redirect(url_for('index'))
   except KeyError:
      return redirect(url_for('index'))

@app.route("/logout",methods=["GET"])
def logout():
    session.pop('username',None)
    session.pop('user_id',None)
    session.clear()
    return render_template("firstpage.html")


@app.route("/book/<bookname>",methods =["GET","POST"])
def book(bookname):
   booksaved = db.execute("SELECT * FROM books WHERE title = :bookname",{"bookname" : bookname}).first()
   reviews = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "EuqunTfdAJnPvtnDprbTkg", "isbns": booksaved.isbn})
   data = reviews.json()
   avg_rating = data["books"][0]["average_rating"]
   ratings_count = data["books"][0]["work_ratings_count"]
   user_reviews = db.execute("SELECT username,isbn,rating,review FROM reviews JOIN account ON reviews.id = account.id WHERE isbn = :isbn",{"isbn" : booksaved.isbn}).fetchall()
   return render_template("book.html",value = booksaved.isbn,title = booksaved.title,year = booksaved.year,author = booksaved.author,isbn = booksaved.isbn,avg_rating = avg_rating,ratings_count=ratings_count,user_reviews = user_reviews,user=session['username'])

@app.route("/book/submitting/<bookname>/<user>",methods = ["POST"])
def submit(bookname,user):
   radiovalues = [request.form.get("rating1"),request.form.get("rating2"),request.form.get("rating3"),request.form.get("rating4"),request.form.get("rating5")]
   review = request.form.get("review")
   val = 0
   for value in radiovalues:
      if value != None:
         val = value
   booksaved = db.execute("SELECT * FROM books WHERE title = :bookname",{"bookname" : bookname}).first()
   user = db.execute("SELECT * FROM account WHERE username = :username",{"username" : user}).first()
   my_review = db.execute("SELECT * FROM reviews WHERE id = :id",{"id" : user.id}).first()
   if val == 0 or review == "":
      return redirect(url_for('book',bookname = bookname))
   else: 
      if my_review is None:
         db.execute("INSERT INTO reviews (id,isbn,rating,review) VALUES (:id, :isbn, :rating, :review)",{"id":user.id , "isbn":booksaved.isbn , "rating":val , "review": review})
         db.commit()
      else:
         db.execute("UPDATE reviews SET isbn=:isbn,rating=:rating,review=:review WHERE id=:id",{"id":user.id , "isbn":booksaved.isbn , "rating":val , "review": review})
         db.commit()
      return redirect(url_for('book',bookname = bookname)) 


@app.route("/api/<isbn>")
def book_api(isbn):
   booksaved = db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn" : isbn}).first()
   review = db.execute("SELECT * FROM reviews WHERE isbn = :isbn",{"isbn" : isbn}).fetchall()
   reviews = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "EuqunTfdAJnPvtnDprbTkg", "isbns": booksaved.isbn})
   data = reviews.json()
   avg_rating = data["books"][0]["average_rating"]
   ratings_count = data["books"][0]["work_ratings_count"]
   ratings = []
   no_of_user_reviews = 0
   for rev in review:
      no_of_user_reviews+=1
      ratings.append(rev.rating)
   complete_average = (sum(ratings)/len(ratings) + float(avg_rating))/2
   complete_number_of_ratings = len(ratings) + float(ratings_count)
   return jsonify({
      "title": booksaved.title,
      "author": booksaved.author,
      "year": booksaved.year,
      "isbn": booksaved.isbn,
      "review_count": complete_number_of_ratings,
      "average_score": complete_average
   })