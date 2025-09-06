from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum

db = SQLAlchemy()

class Users(db.Model):
    id = db.Column("id", db.Integer, primary_key=True, autoincrement=True)
    username = db.Column("username", db.String(100), unique=True, nullable=False)
    email = db.Column("email", db.String(100), unique=True, nullable=False)
    password = db.Column("password", db.String(50), nullable=False)
    full_name = db.Column("full_name", db.String(200), nullable = False)
    phone = db.Column("phone", db.String(15), nullable = False)
    role = db.Column("role", db.String(20), default="User",  nullable=False)
    reservation = db.relationship("ReserveParkingSpot", backref="user", lazy=True, cascade='all, delete')

class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prime_location_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(500), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    maximum_number_of_spots = db.Column(db.Integer, nullable=False)
    spots = db.relationship("ParkingSpot", backref="lot", lazy=True, cascade="all, delete")

class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lot_id = db.Column(db.Integer, db.ForeignKey(ParkingLot.id), nullable=False)
    status = db.Column(Enum("A", "O", name="status_enum"), default="A", nullable=False)
    spot_number = db.Column(db.Integer, nullable=False)
    reservations = db.relationship("ReserveParkingSpot", backref="spot", lazy=True, cascade='all, delete')

class ReserveParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    spot_id = db.Column(db.Integer, db.ForeignKey(ParkingSpot.id), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(Users.id), nullable=False)
    parking_timestamp = db.Column(db.DateTime, nullable=False)
    leaving_timestamp = db.Column(db.DateTime, nullable=False)
    parking_cost_per_unit_time = db.Column(db.Float, nullable=False)
    reservation_status = db.Column(Enum("Active", "Completed", "Cancelled", "Pending", name="reservation_status_enum"), default="Pending", nullable=False)
