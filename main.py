from flask import render_template, request
from classes import Player, Users
from config import app, db
from werkzeug.security import generate_password_hash
from sqlalchemy import exc


@app.route("/", methods=['post', 'get'])
def create():
    if request.method == 'POST':
        country_name = request.form.get('country_name')
        towns_names = [
            request.form.get('t1_name'), request.form.get('t2_name'),
            request.form.get('t3_name'), request.form.get('t4_name')
        ]

        perk = request.form.get('perk')
        if perk is None:
            return render_template("country_country.html")
        else:
            return render_template(
                "success_create.html",
                data=Player(country_name, towns_names, perk)
            )
    return render_template("country_country.html")


@app.route("/create", methods=['post', 'get'])
def main():
    return render_template("main.html")


@app.route("/register", methods=['post', 'get'])
def register():
    if request.method == "POST":
        try:
            password_hash = generate_password_hash(request.form['user_password'])
            new_user = Users(name=request.form['user_name'], password=password_hash)
            db.session.add(new_user)
            db.session.flush()
            db.session.commit()

        except exc.SQLAlchemyError:
            pass

    return render_template("register.html")


if __name__ == "__main__":
    app.run(debug=True)
