import csv
import os

from sqlalchemy import create_engine,exc
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    f=open("books.csv")
    reader = csv.reader(f)
    db.execute("CREATE TABLE books(isbn VARCHAR (10) NOT NULL,title VARCHAR (50) NOT NULL,author VARCHAR (50) NOT NULL,year VARCHAR (4) NOT NULL);")
    for isbn,title,author,year in reader:
        db.execute("INSERT INTO books (isbn,title,author,year) VALUES (:isbn, :title, :author, :year)",{"isbn":isbn , "title":title , "author":author , "year": year})
    db.commit()
if __name__ == "__main__":
    main()
