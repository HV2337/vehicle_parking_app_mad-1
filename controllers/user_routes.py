from flask import Blueprint, redirect, url_for, render_template, session, flash, request, Response
from models.model import *
from datetime import datetime, timedelta
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
import matplotlib.pyplot as plt
import io
import base64
import calendar
from collections import defaultdict

user_bp = Blueprint("user", __name__)

@user_bp.route("/user/dashboard", methods=["GET"])
def user_dashboard():
    if 'user_id' in session:
        user_id = session['user_id']
        lots = ParkingLot.query.all()
        lot_data = []

        for lot in lots:
            available_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status="A").count()
            lot_data.append({
                "id": lot.id,
                "name": lot.prime_location_name,
                "address": lot.address,
                "available_spots": available_spots
            })

        active_reservation = ReserveParkingSpot.query.filter_by(user_id=user_id, reservation_status="Active").all()
        
        return render_template("user_dashboard.html", lots=lot_data, active_reservation=active_reservation)
    
    flash("Please login to access user dashboard","info")
    return redirect(url_for("logout"))


def plot_to_img(fig):
    img = io.BytesIO()
    fig.savefig(img, format='png', bbox_inches="tight")
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode()

@user_bp.route("/user/summary")
def user_summary():
    if 'user_id' in session:
        user_id = session["user_id"]
        reservations = ReserveParkingSpot.query.filter_by(user_id=user_id).filter(ReserveParkingSpot.reservation_status == "Completed").all()
        lot_wise_count = defaultdict(int)
        monthly_count = defaultdict(int)
        duration_by_lot = defaultdict(float)
        total_duration = 0
        total_amount = 0

        for res in reservations:
            lot_name = res.spot.lot.prime_location_name
            lot_wise_count[lot_name] += 1

            if res.leaving_timestamp and res.parking_timestamp:
                duration = (res.leaving_timestamp - res.parking_timestamp).total_seconds() / 3600
                total_duration += duration
                duration_by_lot[lot_name] += duration
                if res.parking_cost_per_unit_time:
                    total_amount += res.parking_cost_per_unit_time*duration
                month = res.parking_timestamp.strftime("%B")
                monthly_count[month] += 1

            

        fig1, ax1 = plt.subplots()
        ax1.bar(lot_wise_count.keys(), lot_wise_count.values())
        ax1.set_title("Lot-wise Parking Frequency")
        img1 = plot_to_img(fig1)

        fig2, ax2 = plt.subplots()
        month_list = list(calendar.month_name)[1:]
        months_sorted = sorted(monthly_count.items(), key=lambda x: month_list.index(x[0]))
        ax2.plot([m[0] for m in months_sorted], [m[1] for m in months_sorted], marker='o')
        ax2.set_title("Monthly Parking Summary")
        img2 = plot_to_img(fig2)

        fig3, ax3 = plt.subplots()
        ax3.bar(duration_by_lot.keys(), duration_by_lot.values(), color='orange')
        ax3.set_title("Total Hours Spent per Lot")
        img3 = plot_to_img(fig3)

        return render_template("user_summary.html",
                                reservations=reservations, 
                                total_duration=round(total_duration, 2), 
                                total_amount=round(total_amount, 2),
                                lot_wise_count=dict(lot_wise_count), 
                                img1=img1,
                                img2=img2,
                                img3=img3)

    flash("Please login to access user dashboard","info")
    return redirect(url_for("logout"))



@user_bp.route("/user/<int:lot_id>/reserve_spot")
def reserve_spot(lot_id):
    if 'user_id' in session:
        user_id = session['user_id']
        available_spot = ParkingSpot.query.filter_by(lot_id=lot_id, status="A").first()

        if not available_spot:
            flash("No available spots in this lot.", "error")
            return redirect(url_for("user.user_dashboard"))
        
        try:
            available_spot.status = "O"
            lot = ParkingLot.query.get(lot_id)
            price = lot.price

            now = datetime.now()
            reservation = ReserveParkingSpot(
                spot_id=available_spot.id,
                user_id=user_id,
                parking_timestamp=now,
                leaving_timestamp=now + timedelta(days=1),  # Placeholder
                parking_cost_per_unit_time=price,
                reservation_status="Active"
            )

            db.session.add(reservation)
            db.session.commit()
            flash("Spot reserved successfully!", "success")
            return redirect(url_for("user.user_dashboard"))
        except IntegrityError:
            db.session.rollback()
            flash("Unable to Reserve a Spot in the lot!", "error")
            return redirect(url_for('user.user_dashboard'))

    flash("Please login to access user dashboard","info")
    return redirect(url_for("logout"))

@user_bp.route("/user/<int:reservation_id>/release_spot")
def release_spot(reservation_id):
    if 'user_id' in session:
        reservation = ReserveParkingSpot.query.get(reservation_id)

        if not reservation or reservation.reservation_status != "Active":
            flash("Invalid reservation or already released.", "error")
            return redirect(url_for("user.user_dashboard"))
        try:

            leaving_time = datetime.now()
            reservation.leaving_timestamp = leaving_time

            duration = leaving_time - reservation.parking_timestamp
            duration_hours = duration.total_seconds() / 3600

            total_cost = round(duration_hours * reservation.parking_cost_per_unit_time, 2)

            db.session.commit()
            flash(f"Total cost: {total_cost} Pay the amount and release the spot!", "success")
            return redirect(url_for('user.payment_page', reservation_id=reservation.id, amount=total_cost))

        except IntegrityError:
            db.session.rollback()
            flash("Unable to release the spot! Please Try again!", "error")
            return redirect(url_for('user.release_spot', reservation_id=reservation_id))

    flash("Please login to access user dashboard","info")
    return redirect(url_for("logout"))

@user_bp.route("/user/<int:reservation_id>/<float:amount>/payment_page", methods=["GET", "POST"])
def payment_page(reservation_id, amount):
    if 'user_id' in session:
        user_id = session['user_id']
        user=Users.query.filter(Users.id==user_id).first()
        reservation = ReserveParkingSpot.query.get(reservation_id)
        if not reservation or reservation.reservation_status != "Active":
            flash("Invalid reservation or already released.", "error")
            return redirect(url_for("user.user_dashboard"))
        if request.method == "POST":
            flash("Payment Successfull!", "success")#its dummy so no worries 
            try:
                reservation.reservation_status = "Completed"
                reservation.spot.status = "A"
                db.session.commit()
                flash("Spot Released Successfully!", "success")
                return redirect(url_for("user.user_dashboard"))
            except IntegrityError:
                db.session.rollback()
                flash("Unable to release the spot! Please Try again!", "error")
                return redirect(url_for('user.release_spot', reservation_id=reservation_id))
        else:
            return render_template("payment_page.html", id=reservation_id, price=amount, name=user.full_name, email=user.email)
    
    flash("Please login to access user dashboard","info")
    return redirect(url_for("logout"))

@user_bp.route("/user/<int:lot_id>/view_lot")
def view_lot_details(lot_id):
    if 'user_id' in session:
        lot = ParkingLot.query.get_or_404(lot_id)
        spots = ParkingSpot.query.filter_by(lot_id=lot_id).all()
        return render_template("view_lot_user.html", lot=lot, spots=spots)
    
    flash("Please login to access user dashboard","info")
    return redirect(url_for("logout"))