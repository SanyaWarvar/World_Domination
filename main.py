from flask import render_template, request, url_for
from flask_login import login_required, login_user, current_user
from classes import Lobby, LobbyPlayer, Town, Users
from config import app, db
from sqlalchemy import exc


@app.route("/create", methods=['post', 'get'])
@login_required
def create():
    if current_user.current_country_id:

        return app.redirect(url_for("play", country_id=current_user.current_country_id))

    if request.method == 'POST':
        country_name = request.form.get('country_name')
        towns_names = [
            request.form.get('t1_name'), request.form.get('t2_name'),
            request.form.get('t3_name'), request.form.get('t4_name')
        ]

        perk = request.form.get('perk')

        if perk is None:
            return render_template("country_country.html", message="Перк не выбран")

        lobby_id = request.form.get('lobby_id')
        if len(db.session.query(LobbyPlayer).filter_by(lobby_id=lobby_id).all()) == 0:

            new_lobby = Lobby(title=str(lobby_id))
            new_lobby.round_num = 1
            db.session.add(new_lobby)
            db.session.flush()
        else:
            country_name_in_lobby = [
                country.country_name for country in LobbyPlayer.query.filter_by(lobby_id=lobby_id).all()
            ]
            if country_name in country_name_in_lobby:
                message = "Название страны уже занято!"
                return render_template("country_country.html", message=message)

        new_player = LobbyPlayer(lobby_id=int(request.form.get('lobby_id')), country_name=country_name, perk=perk)

        db.session.add(new_player)
        db.session.flush()

        town_names_in_lobby = []
        for player in LobbyPlayer.query.filter_by(lobby_id=lobby_id).all():
            t = Town.query.filter_by(country_id=player.id).all()
            names = [town.name for town in t]
            for name in names:
                town_names_in_lobby.append(name)

        for name in towns_names:
            if name in town_names_in_lobby:
                db.session.rollback()
                return render_template("country_country.html", message="Название города/городов занято")

            if name == towns_names[0]:
                quality = 75
            else:
                quality = 50

            db.session.add(Town(country_id=new_player.id, name=name, quality=quality))

        current_user.current_country_id = new_player.id
        new_player.perk_change()
        db.session.add(current_user)
        db.session.flush()
        db.session.commit()

        return app.redirect(url_for("play", country_id=new_player.id))

    return render_template("country_country.html", message="")


@app.route("/play/<country_id>", methods=['POST', 'GET'])
@login_required
def play(country_id):

    if current_user.current_country_id is not int(country_id) and current_user.role != "admin":
        return app.redirect(url_for("play", country_id=current_user.current_country_id))

    player = LobbyPlayer.query.filter_by(id=country_id).first()
    towns = Town.query.filter_by(country_id=country_id).all()
    lobby = Lobby.query.filter_by(title=player.lobby_id).first()
    if request.method == 'POST':
        # улучшения
        if request.form.get("upg"):
            upg_t = Town.query.filter_by(id=request.form.get(f"upg")).first()
            if player.money >= player.upg_cost and upg_t.quality > 0:
                upg_t.quality_next += player.upg_power

                player.money -= player.upg_cost
                player.money_mltp += player.money_mltp_power
                player.money_mltp = min(round(player.money_mltp, 2), 3.6)

                db.session.add(upg_t)
                db.session.add(player)
                db.session.commit()

                if player.perk == "Золотой телец":

                    lobby.eco_next -= 2.5
                    db.session.add(lobby)
                    db.session.commit()

        # покупка щитов
        if request.form.get("shld"):
            shld_t = Town.query.filter_by(id=request.form.get(f"shld")).first()
            if player.money >= player.shield_cost and shld_t.shield == 0 and shld_t.shield_next == 0 \
                    and player.perk != "Берсерк" and shld_t.quality > 0:
                shld_t.shield_next = 1
                player.money -= player.shield_cost
                db.session.add(shld_t)
                db.session.add(player)
                db.session.commit()

        if request.form.get("shld_extra"):
            shld_t = Town.query.filter_by(id=request.form.get(f"shld_extra")).first()
            if player.money >= player.shield_cost and shld_t.shield < 3 and shld_t.shield_next < 3 \
                    and player.perk == "Джимми Нейтрон" and shld_t.quality > 0:
                shld_t.shield_next = 3
                player.money -= player.shield_cost
                db.session.add(shld_t)
                db.session.add(player)
                db.session.commit()

        if request.form.get("nuke"):
            if player.money >= player.nuke_cost and player.nuke == "Нет" and \
                    player.nuke_next == "Не будет" and player.perk != "Пацифист":
                player.nuke_next = "Будет"
                player.money -= player.nuke_cost
                db.session.add(player)
                db.session.commit()

        if request.form.get("bomb"):
            if player.money >= player.bombs_cost and player.nuke == "Есть":
                player.bombs_count_next += 1
                player.money -= player.bombs_cost
                db.session.add(player)
                db.session.commit()

        if request.form.get("ready"):
            player.is_ready = 1
            db.session.add(player)
            db.session.commit()
            all_ready = True
            for p in LobbyPlayer.query.filter_by(lobby_id=player.lobby_id).all():
                if p.is_ready == 0:
                    all_ready = False
                    break
            if all_ready:
                lobby.round()

        if request.form.get("money_send"):
            m = request.form.get("money_send")
            is_int = True
            try:
                m = int(m)
            except ValueError:
                is_int = False

            if is_int and player.money >= m > 0:
                player.money -= m
                target = LobbyPlayer.query.filter_by(id=request.form.get("country_send")).first()
                target.money += m
                db.session.add(player)
                db.session.add(target)
                db.session.commit()

        # обработка атаки(выбор целей)

        if request.form.get(f"atk"):
            if player.bombs_count > 0:
                target = Town.query.filter_by(id=request.form.get(f"atk")).first()
                player.atk += f"|{target.id}|"
                db.session.add(player)
                db.session.commit()

                if player.perk != "Друид":

                    lobby.eco_next = -10
                    db.session.add(lobby)
                    db.session.commit()
                if player.perk == "Берсерк":
                    for i in range(3):
                        target.under_attack()

                target.under_attack()
                player.bombs_count -= 1
                db.session.add(target)
                db.session.add(player)
                db.session.commit()

        if request.form.get("sanct"):
            c = request.form.get("sanct")
            victim = LobbyPlayer.query.filter_by(id=c).first()
            if player.country_name not in (victim.sanctions_next or victim.sanctions) \
                    and player.perk != "Джимми Нейтрон":
                if victim.sanctions == "" and victim.sanctions_next == "":
                    victim.sanctions_next += player.country_name
                else:
                    victim.sanctions_next += f"|{player.country_name}|"
                db.session.add(victim)
                db.session.commit()

        if request.form.get("spy"):
            if player.money >= player.spy_cost:
                player.money -= player.spy_cost
                player.spy = request.form.get("spy")
                db.session.add(player)
                db.session.commit()

        if request.form.get("eco_up"):
            if player.money >= 200:
                player.money -= 200

                lobby.eco_next += 20
                db.session.add(lobby)
                db.session.add(player)
                db.session.commit()

    return render_template(
        "success_create.html",
        db=db, towns=towns, player=player, LobbyPlayer=LobbyPlayer, Town=Town, Lobby=Lobby, str=str
    )


@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == "POST":
        password = request.form.get("user_password")
        name = request.form.get("user_name")
        target_user = Users.query.filter_by(name=name).first()
        if target_user.password == password:
            login_user(target_user)

            return app.redirect(url_for("cabinet", id=target_user.id))
    return render_template("login.html")


@app.route("/register", methods=['post', 'get'])
def register():
    if request.method == "POST":
        try:
            new_user = Users(name=request.form['user_name'], password=request.form['user_password'])
            db.session.add(new_user)
            db.session.flush()
            db.session.commit()
        except exc.SQLAlchemyError:
            db.session.rollback()
            return render_template("register.html", message="Пользователь с таким именем уже есть")
        login_user(new_user)
        return app.redirect(url_for("cabinet", id=new_user.id))
    return render_template("register.html", message="")


@app.route("/", methods=['post', 'get'])
def main():
    return render_template("main.html")


@app.route("/cabinet/<user_id>", methods=['post', 'get'])
@login_required
def cabinet(user_id):

    if current_user.id == int(user_id):
        return render_template("cabinet.html")
    else:
        return app.redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
