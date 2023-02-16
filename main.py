from flask import Flask, render_template, request, flash
from classes import Player


app = Flask(__name__)


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


if __name__ == "__main__":
    app.run(debug=True)
