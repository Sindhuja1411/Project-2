from pymongo import MongoClient
from flask import Flask
from flask import request
from flask import jsonify
import time
import hashlib
from datetime import datetime, timedelta
import jwt
import flask

client = MongoClient('localhost', 27017)

app = Flask(__name__)
app.config["DEBUG"] = True

database = client.libuser
user_details = database.user_details
book_details = database.book_details

def token_required(f):
    def decorated(*args, **kwargs):
        headers = flask.request.headers
        bearer_token = headers.get('Authorization')
        token = bearer_token.split()[1]
        print(token)
        if token:

            secret_key = 'abcd'
            decoded = jwt.decode(token, secret_key, options={'verify_exp': False})
            print(decoded)
            global valid_user
            valid_user = user_details.find_one({'email': decoded['user']})
            print(valid_user)
            return f(*args, **kwargs)
        elif not token:
            print("in elif")
            return jsonify({'message': 'Unsuccessful Authentication'}), 401
    decorated.__name__ = f.__name__
    return decorated

@app.route('/lib/welcome', methods=['POST'])
def main():
    today = datetime.now()
    return jsonify({"message": "Welcome to the LIBRARY",
                    "The current date & time is ": today})


@app.route('/lib/register_user', methods=['POST'])

def register():
     register_user = {
        'name': request.json['name'],
         'address': request.json['address'],
         'email': request.json['email'],
        'contactno': request.json['contactno'],
         'password': request.json['password'],
        'available': "true"
    }
     salt = "5gz"
     db_password = register_user['password'] + salt
     print(db_password)
     h = hashlib.md5(db_password.encode())
     print(h)
     hashed = h.hexdigest()
     print(hashed)
     register_user['password'] = hashed
     user_details.insert_one(register_user)
     return({'message':"You are a member of this library"})

@app.route('/lib/user_login', methods=['POST'])

def login():
    user_login = {
        'email': request.json['email'],
        'password': request.json['password'],
        }
    check_user = user_details.find_one({'email': user_login['email']})
    print(check_user)
    salt = "5gz"
    entered_password = user_login['password'] + salt
    print(entered_password)
    h = hashlib.md5(entered_password.encode())
    print(h)
    hashed = h.hexdigest()
    print(hashed)
    user_login['password'] = hashed
    if(check_user['password']==user_login['password']):
        print("in if")
        secret_key = 'abcd'
        payload = {'user': check_user['email'], 'exp': time.time() + 300}
        jwt_token = jwt.encode(payload, secret_key)
        print(jwt_token)
        response = {
            'token': jwt_token.decode()
        }
        print(response)
        return jsonify({"message": "login success", "data": response})
    else:
        return jsonify({"message": "Name/password mismatch.. Pls try again"})


@app.route('/lib/update/user_details', methods=['POST'])
@token_required
def update_user():
    new_address = {'address': request.json['address']}
    print(new_address)
    new_contact = {'contactno': request.json['contactno']}
    print(new_contact)
    user_details.update_one(valid_user, {'$set': {'address': new_address['address'], 'contactno': new_contact['contactno']}})
    return jsonify({"message": "Details are updated"})

@app.route('/lib/delete/user', methods=['POST'])
@token_required
def cancel_membership():
    b = book_details.aggregate(
        [{'$match': {'name': valid_user['name']}},
         {'$group': {'_id': 'null', 'count': {'$sum': 1}}}
         ]
    )
    c = list(b)
    print(c)
    if len(c) == 0:
        print("in if")
        del_user = user_details.find_one_and_delete({'name': valid_user['name']})
        print(del_user)
        return jsonify({"message": "Your membership is cancelled"})
    elif c[0]['count'] <= 3:
        print("in elif")
        return jsonify({"message": "Please return the borrowed book to cancel your membership"})


@app.route('/book/donate', methods=['POST'])
@token_required
def donate():
     donate_book = {
        'id': request.json['id'],
        'name_of_book': request.json['name'],
        'author': request.json['author'],
         'available': "true"
    }
     book_details.insert_one(donate_book)
     return({'message':"Book inserted"})

@app.route('/book/borrow/bookname', methods=['POST'])
@token_required
def getBook():
    get_book = {'name': request.json['name_of_book']}
    x = book_details.find_one({'name_of_book': get_book['name']})
    print(x)

    b = book_details.aggregate(
                                [{'$match': {'name': valid_user['name']}},
                                 {'$group': {'_id': 'null', 'count': {'$sum': 1}}}
                                 ]

    )
    c = list(b)
    print(c)
    if len(c) == 0 or c[0]['count'] < 3 and x['available'] == "true":
        print("in not")
        borrow_date = datetime.now()
        print(borrow_date)
        chk_return = datetime.now() + timedelta(days=1)
        print(chk_return)
        book_details.update_one({'name_of_book': x['name_of_book']},
                                {'$set': {'available': 'false', 'name': valid_user['name'], 'date_to_return': chk_return}})
        return jsonify({"message": "The book is available to borrow, The last date to return this book is", "data": chk_return })
    elif c[0]['count'] == 3:
        print("in 1st if")
        return({"message": "Limit is met.."})
    elif x['available'] == "false":
        print("in elif")
        return jsonify({"Message": "Book is not available to borrow"})
    else:
        print("in else")
        return jsonify({"Message": "Enter a valid input"})

@app.route('/book/renew/bookname', methods=['POST'])
@token_required
def get_book_name():
    get_book_torenew = {'name': request.json['name']}
    x = book_details.find_one({'name_of_book': get_book_torenew['name']})
    print(x)
    return_date = datetime.now()
    chk_return = return_date + timedelta(days=1)
    print(chk_return)
    if x['available'] == "false" and x['date_to_return'] >= return_date:
        print("in if")
        book_details.update_one({'name_of_book': x['name_of_book']}, {'$set': {"date_to_return": "", "date_to_return": chk_return}})
        return jsonify({"message": "The book is renewed"})
    elif x['date_to_return'] < return_date:
        book_details.update_one({'name_of_book': x['name_of_book']}, {'$set': {"date_to_return": "", "date_to_return": chk_return}})
        return jsonify({"Message": "Please pay the fine of Rs.10 to renew the book as return is overdue"})
    else:
        return jsonify({"message": "The book cannot be renewed, as it's not borrowed..Enter a valid name"})

@app.route('/book/return/bookname', methods=['POST'])
@token_required
def returnBook():
    return_book = {'name': request.json['name']}
    return_date = datetime.now()
    print(return_date)
    x = book_details.find_one({'name_of_book': return_book['name']})
    print(x)
    if x['available'] == "false" and x['date_to_return'] >= return_date:
        print("in if")
        book_details.update_one({'name_of_book': x['name_of_book']}, {'$set': {'available': 'true', 'name': "", "date_to_return": ""}})
        return jsonify({"message": "The book is returned on time"})
    elif x['date_to_return'] < return_date:
        book_details.update_one({'name_of_book': x['name_of_book']}, {'$set': {'available': 'true', 'name': "", "date_to_return": ""}})
        return jsonify({"Message": "Please pay the fine of Rs.10 as book return is overdue"})
    elif x['available'] == "true":
        print("in elif")
        return jsonify({"Message": "Book is available to borrow"})
    else:
        print("in else")
        return jsonify({"Message": "Enter a valid input"})

@app.route('/book/lost/deletebook', methods=['POST'])
@token_required
def delete_book():
    delete_book = ({'name': request.json['name']})
    print(delete_book)
    name_of_deleted_book = book_details.find_one_and_delete(delete_book)
    return jsonify({"Message": "This book is deleted", "data": name_of_deleted_book})

app.run()
