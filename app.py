from sqlalchemy import or_
from flask import Flask, redirect, url_for, render_template, session, flash, request
from flask_sqlalchemy import SQLAlchemy
from models.model import *
from sqlalchemy.exc import IntegrityError
from controllers.admin_routes import admin_routes
from controllers.user_routes import user_bp

app = Flask(__name__)

app.secret_key = "diefknkfjqeirfjqefjnjwufhilqewiijnjaiojweroijnsidnncknwefoqe[porjfoipjqncepiomoijcemfoiqieofjoqjnoifjiopqrnjgoiwjeroigjeroij]"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///vehicle-parking.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    existing_user = Users.query.filter_by(role="Admin").first()
    if not existing_user:
        admin_user = Users(username = "hari", email="hariadmin@gmail.com", password="adminhari", role="Admin", full_name="Hareesh V", phone="0000000000")
        db.session.add(admin_user)
        db.session.commit()
@app.route("/")
def home():
    if 'user_id' in session:
        user = Users.query.filter(Users.id == session['user_id']).first()
        return render_template('home_logged.html', user=user)
    
    return render_template('home_notlogged.html')

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        fname = request.form['fname']
        mname = request.form['mname']
        lname = request.form['lname']
        phone = request.form['phone']

        full_name = f"{fname} {mname} {lname}".strip() if mname and mname.strip() else f"{fname} {lname}"

        existing_username = Users.query.filter(Users.username == username).first()
        existing_email = Users.query.filter(Users.email == email).first()
        if existing_username:
            if existing_username.role == "Admin":
                flash("Admin  already exists Please Login!", "info")
                session['user_id'] = existing_username.id
                return redirect(url_for('login', identifier=existing_username.username))
            else:
                flash("Username already exists!", "info")
                return redirect(url_for('signup'))
        if existing_email:
            session['user_id'] = existing_email.id
            flash("Email already registered.... Please Login!", "info")
            return redirect(url_for('login', identifier=existing_email.email))
        
        #adding new user to database
        try:
            new_user=Users(username=username, email=email, password=password, full_name=full_name, phone=phone, role="User")
            db.session.add(new_user)
            db.session.commit()
            flash("Your account was created successfully","Success")
            session['user_id']=new_user.id
            return redirect(url_for('login', identifier=new_user.username))
        
        except IntegrityError:
            db.session.rollback()
            flash("Something Went wrong during signup Please try again","error")
            return redirect(url_for('signup'))
        

    else:
        return render_template("signup.html")
    

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form['identifier']
        password = request.form['password']
        user = Users.query.filter(or_(Users.username == identifier, Users.email == identifier)).first()
        if user and user.password == password:
            session['user_id'] = user.id
            return redirect('/dashboard')
        elif user and user.password != password:
            flash("Invalid Password!","error")
            return redirect(url_for('login', identifier=identifier))
        else:
            flash("User Not Found! Please Try Again", "error")
            return redirect(url_for('login'))
        
    return render_template("login.html")
            
@app.route("/dashboard", methods=["GET"])
def dashboard():
    if request.method=="GET":
        if 'user_id' in session:
            user = Users.query.filter(Users.id == session['user_id']).first()
            if user.role == "Admin":
                return redirect(url_for('admin_routes.admin_dashboard'))
            else:
                return redirect(url_for('user.user_dashboard'))
    flash("Please login to access this page!", "info")
    return redirect(url_for("logout"))


@app.route("/logout")
def logout():
    if 'user_id' in session:
        user_id = session['user_id']
        user = Users.query.filter(Users.id == user_id).first()
        flash(f"{user.username} You have been logged out!", "info")
    session.pop("user_id", None)
    return redirect(url_for("login"))

app.register_blueprint(admin_routes)

app.register_blueprint(user_bp)



if __name__ == '__main__':
    app.run(debug=True)