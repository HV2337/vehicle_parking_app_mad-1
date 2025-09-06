from flask import Blueprint, redirect, url_for, render_template, session, flash, request, Response
from models.model import *
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
import matplotlib.pyplot as plt
import base64
import io
from collections import Counter

admin_routes = Blueprint('admin_routes', __name__)

@admin_routes.route("/admin/dashboard", methods=["GET"])
def admin_dashboard():
    if 'user_id' in session:
        user = Users.query.filter(Users.id == session['user_id']).first()
        if user.role != "Admin":
            flash("You are not allowed to visit this page!", "warning")
            return redirect(url_for('dashboard'))
        else:
            lots = ParkingLot.query.all()
            lot_data = []
            for lot in lots:
                total_spots = lot.maximum_number_of_spots
                available_spots = len([s for s in lot.spots if s.status == "A"])
                occupied_spots = total_spots - available_spots
                lot_data.append({
                    'id': lot.id,
                    'name': lot.prime_location_name,
                    'price': lot.price,
                    'address': lot.address,
                    'pincode': lot.pincode,
                    'total': total_spots,
                    'available': available_spots,
                    'occupied': occupied_spots
                })

            return render_template("admin_dashboard.html", user=user, lot_data=lot_data)
        
    flash("Please login to access admin dashboard","info")
    return redirect(url_for("logout"))

@admin_routes.route("/admin/search", methods=["GET", "POST"])
def admin_search():
    if 'user_id' in session:
        user = Users.query.filter(Users.id == session['user_id']).first()
        if user.role != "Admin":
            flash("You are not allowed to visit this page!", "warning")
            return redirect(url_for('dashboard'))
        else:
            users = []
            spots = []
            query = request.form.get('query','').strip() if request.method == "POST" else ""

            if query:
                users = Users.query.filter(
                    (Users.username.ilike(f"%{query}%")) |
                    (Users.email.ilike(f"%{query}%"))
                ).all()

                spots = ParkingSpot.query.filter(
                    (ParkingSpot.status.ilike(f"%{query}%")) |
                    (ParkingSpot.id.ilike(f"%{query}%"))
                ).all()

                if query and not users and not spots:
                    flash("No matches found.", "info")

            return render_template("admin_search.html", user=user, query=query, users=users, spots=spots)

    flash("Please login to access admin dashboard","info")
    return redirect(url_for("logout"))

@admin_routes.route("/admin/summary")
def admin_summary():
    if 'user_id' in session:
        user = Users.query.filter(Users.id == session['user_id']).first()
        if user.role != "Admin":
            flash("You are not allowed to visit this page!", "warning")
            return redirect(url_for('dashboard'))
        else:
            lots = ParkingLot.query.all()
            total_lots = len(lots)
            total_spots = sum([len(lot.spots) for lot in lots])
            total_available = ParkingSpot.query.filter_by(status="A").count()
            total_occupied = ParkingSpot.query.filter_by(status="O").count()

            reservations = ReserveParkingSpot.query.all()
            reservation_counts = Counter([res.reservation_status for res in reservations])

            # Prepare data for graphs
            def encode_plot(fig):
                img = io.BytesIO()
                fig.savefig(img, format='png')
                img.seek(0)
                return base64.b64encode(img.getvalue()).decode()
            
            if total_spots == 0:
                flash("No parking lots or spots have been added yet.", "info")
                return render_template("admin_summary.html", user=user, no_data=True)
            else:
                fig1, ax1 = plt.subplots()
                ax1.pie([total_available, total_occupied], labels=["Available", "Occupied"], autopct='%1.1f%%', colors=["green", "red"])
                ax1.set_title("Spot Availability")
                plot1 = encode_plot(fig1)
                plt.close(fig1)

                fig2, ax2 = plt.subplots()
                ax2.bar(reservation_counts.keys(), reservation_counts.values(), color='skyblue')
                ax2.set_title("Reservation Status Overview")
                ax2.set_xlabel("Status")
                ax2.set_ylabel("Count")
                plot2 = encode_plot(fig2)
                plt.close(fig2)

                return render_template("admin_summary.html",
                            user=user,
                            total_lots=total_lots,
                            total_spots=total_spots,
                            total_available=total_available,
                            total_occupied=total_occupied,
                            reservation_counts=reservation_counts,
                            plot1=plot1,
                            plot2=plot2)


    flash("Please login to access admin dashboard","info")
    return redirect(url_for("logout"))


def create_spots(lot_id):
    lot = ParkingLot.query.get(lot_id)
    if lot:
        max_spots = lot.maximum_number_of_spots
        for i in range(1, max_spots+1):
            exists = ParkingSpot.query.filter_by(lot_id = lot.id, spot_number=i).first()
            status = "A"
            if not exists:
                new_spot = ParkingSpot(lot_id=lot.id, status=status, spot_number=i)
                db.session.add(new_spot)
        db.session.commit()
        return "created"
    return "error"


@admin_routes.route("/admin/create_lot", methods=["GET", "POST"])
def create_lot():
    if 'user_id' in session:
        user=Users.query.filter(Users.id == session['user_id']).first()
        if user.role != "Admin":
            flash("You are not allowed to visit this page!","warning")
            return redirect(url_for('dashboard'))
        else:
            if request.method=="POST":
                prime_location = request.form['prime_location']
                price = float(request.form['price'])
                address = request.form['address']
                pincode = request.form['pincode']
                max_spots = int(request.form['max_spots'])

                try:
                    new_lot = ParkingLot(prime_location_name=prime_location, price=price, address=address, pincode=pincode, maximum_number_of_spots=max_spots)
                    db.session.add(new_lot)
                    db.session.commit()
                    spot_creation = create_spots(new_lot.id)
                    if spot_creation == "created":
                        flash("Parking lot and spots created successfully", "info")
                        return redirect(url_for('admin_routes.view_lot', lot_id = new_lot.id))
                    else:
                        flash("Something Went wrong!", "error")
                        return redirect(url_for('admin_routes.create_lot'))
                
                except IntegrityError:
                    db.session.rollback()
                    flash("Parking lot already exists!", "info")
                    return redirect(url_for('admin_routes.create_lot'))
                
            else:
                return render_template("create_lot.html")
    else:
        flash("Please Login to Access the page","info")
        return redirect(url_for('logout'))


@admin_routes.route("/admin/<int:lot_id>/edit_lot", methods=["GET", "POST"])
def edit_lot(lot_id):
    if 'user_id' in session:
        user=Users.query.filter(Users.id == session['user_id']).first()
        if user.role != "Admin":
            flash("You are not allowed to visit this page!","warning")
            return redirect(url_for('dashboard'))
        else:
            lot = ParkingLot.query.get(lot_id)
            if request.method=="POST":
                if lot:
                    old_max_spot = lot.maximum_number_of_spots
                    prime_location = request.form['prime_location']
                    price = float(request.form['price'])
                    address = request.form['address']
                    pincode = request.form['pincode']
                    new_max_spots = int(request.form['max_spots'])
                    try:
                        lot.prime_location_name = prime_location
                        lot.price = price
                        lot.address = address
                        lot.pincode = pincode

                        if new_max_spots > old_max_spot:
                            for i in range(old_max_spot+1, new_max_spots+1):
                                exists = ParkingSpot.query.filter_by(lot_id = lot.id, spot_number=i).first()
                                status = "A"
                                if not exists:
                                    new_spot = ParkingSpot(lot_id=lot.id, status=status, spot_number=i)
                                    db.session.add(new_spot)
                        elif new_max_spots < old_max_spot:
                            for i in range(new_max_spots, old_max_spot+1):
                                exists = ParkingSpot.query.filter_by(lot_id = lot.id, spot_number=i).first()
                                if exists and exists.status == "A":
                                    db.session.delete(exists)
                                else:
                                    flash("Cannot reduce spot count some spots are occupied!", "warning")
                                    return redirect(url_for('admin_routes.view_lot', lot_id=lot.id))
                        else:
                            pass
                        lot.maximum_number_of_spots=new_max_spots
                        db.session.commit()
                        flash("Parking lot updated successfully!", "success")
                        return redirect(url_for('admin_routes.view_lot', lot_id=lot.id))

                    except IntegrityError:
                        db.session.rollback()
                        flash("Parking lot already exists!", "info")
                        return redirect(url_for('admin_routes.view_lot', lot_id = lot.id))
                else:
                    flash("Parking lot does not exists!", "info")
                    return redirect(url_for('admin_routes.admin_dashboard'))

            else:
                if lot:
                    return render_template("edit_lot.html", lot_id = lot_id, prime_location=lot.prime_location_name, price=lot.price, address=lot.address, pincode=lot.pincode, max_spots=lot.maximum_number_of_spots)
                else:
                    flash("Parking lot does not exists!", "info")
                    return redirect(url_for('admin_routes.create_lot'))

    else:
        flash("Please Login to Access the page","info")
        return redirect(url_for('logout'))

@admin_routes.route("/admin/<int:lot_id>/delete_lot", methods = ["GET","POST"])
def delete_lot(lot_id):
    if 'user_id' in session:
        user=Users.query.filter(Users.id == session['user_id']).first()
        if user.role != "Admin":
            flash("You are not allowed to visit this page!","warning")
            return redirect(url_for('dashboard'))
        else:
            lot = ParkingLot.query.get(lot_id)
            
            if lot:
                occupied = ParkingSpot.query.filter(ParkingSpot.lot_id == lot.id, ParkingSpot.status != "A").first()
                if occupied:
                    flash("Cannot delete lot. One or more spots are occupied.", "error")
                    return redirect(url_for('admin_routes.view_lot', lot_id=lot.id))
                try:
                    db.session.delete(lot)
                    db.session.commit()
                    flash("Parking lot deleted successfully!", "success")
                    return redirect(url_for('admin_routes.admin_dashboard'))
                except:
                    db.session.rollback()
                    flash("Error occurred while deleting the lot.", "error")
            else:
                flash("Parking lot not found!", "info")
                return redirect(url_for('admin_routes.admin_dashboard'))
            
    else:
        flash("Please Login to Access the page","info")
        return redirect(url_for('logout'))
    

@admin_routes.route("/admin/<int:lot_id>/view_lot", methods=["GET"])
def view_lot(lot_id):
    if 'user_id' in session:
        user=Users.query.filter(Users.id == session['user_id']).first()
        if user.role != "Admin":
            flash("You are not allowed to visit this page!","warning")
            return redirect(url_for('dashboard'))
        else:
            lot = ParkingLot.query.get_or_404(lot_id)
            spots = ParkingSpot.query.filter_by(lot_id=lot.id).order_by(ParkingSpot.spot_number).all()

            # Count spot status
            available_count = sum(1 for s in spots if s.status == "A")
            occupied_count = sum(1 for s in spots if s.status == "O")

            # Generate pie chart
            labels = ['Available', 'Occupied']
            values = [available_count, occupied_count]
            colors = ['green', 'red']

            fig, ax = plt.subplots()
            ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
            ax.axis('equal')
            chart_path = f"static/lot_{lot.id}_status_pie.png"
            plt.savefig(chart_path)
            plt.close()

            # Spot + reservation data
            spot_data = []
            for spot in spots:
                latest_reservation = (ReserveParkingSpot.query
                                    .filter_by(spot_id=spot.id)
                                    .order_by(ReserveParkingSpot.parking_timestamp.desc())
                                    .first())
                spot_data.append({
                    'spot': spot,
                    'latest_reservation': latest_reservation
                })

            return render_template("view_lot.html", user=user, lot=lot,
                                spot_data=spot_data,
                                pie_chart_url=chart_path)



    else:
        flash("Please Login to Access the page","info")
        return redirect(url_for('logout'))

@admin_routes.route("/admin/<int:spot_id>/view_spot", methods=["GET"])
def view_spot(spot_id):
    if 'user_id' in session:
        user=Users.query.filter(Users.id == session['user_id']).first()
        if user.role != "Admin":
            flash("You are not allowed to visit this page!","warning")
            return redirect(url_for('dashboard'))
        else:
            spot = ParkingSpot.query.get_or_404(spot_id)
    
            reservations = ReserveParkingSpot.query.filter_by(spot_id=spot.id).order_by(ReserveParkingSpot.parking_timestamp.desc()).all()
            
            return render_template("view_spot.html", spot=spot, reservations=reservations)

    else:
        flash("Please Login to Access the page","info")
        return redirect(url_for('logout'))

@admin_routes.route("/admin/view_users")
def list_users():
    if 'user_id' in session:
        user=Users.query.filter(Users.id == session['user_id']).first()
        if user.role != "Admin":
            flash("You are not allowed to visit this page!","warning")
            return redirect(url_for('dashboard'))
        else:
            users = Users.query.filter(Users.role=="User").all()
            return render_template("admin_userslist.html", users=users)
        
    else:
        flash("Please Login to Access the page","info")
        return redirect(url_for('logout'))
    

@admin_routes.route("/admin/<int:user_id>/view_user")
def view_user(user_id):
    if 'user_id' in session:
        user=Users.query.filter(Users.id == session['user_id']).first()
        if user.role != "Admin":
            flash("You are not allowed to visit this page!","warning")
            return redirect('/dashboard')
        else:
            target_user = Users.query.get(user_id)
            reservations = ReserveParkingSpot.query.filter_by(user_id=target_user.id).all()
            return render_template("view_user.html", user=target_user, reservations=reservations)
        
    else:
        flash("Please Login to Access the page","info")
        return redirect(url_for('logout'))
