from flask import render_template, request, url_for, redirect
from flask_login import login_required, login_user, current_user, logout_user
from classes import Lobby, LobbyPlayer, Town, Users, Final
from config import app, db
from sqlalchemy import exc


@app.route("/new_lobby", methods=['post', 'get'])
@login_required
def new_lobby():
    if request.method == 'POST':
        lobby_name = request.form.get('lobby_name')
        lobby_password = request.form.get('lobby_password')
        if lobby_password is None:
            lobby_password = ""

        # переписать проверку названий городов и стран по такому же принципу
        if Lobby.query.filter_by(title=lobby_name).first():
            return render_template("lobby_create.html", message="Ошибка! Название лобби уже занято", user=current_user)
        if len(lobby_name) > 20 or len(lobby_password) > 20:
            return render_template("lobby_create.html",
                                   message="Ошибка Название или пароль превышают максимальную длину",
                                   user=current_user)
        try:
            player_count = int(request.form.get('player_count'))
            end_round = int(request.form.get('end_round'))
        except ValueError:
            return render_template("lobby_create.html", message="Ошибка! Введите целое число", user=current_user)

        new_final = Final()
        db.session.add(new_final)
        db.session.commit()

        new = Lobby(
            title=lobby_name, password=lobby_password,
            player_count=player_count, end_round=end_round, final_id=new_final.id
        )

        db.session.add(new)
        db.session.commit()


        return redirect(url_for("create"))

    return render_template("lobby_create.html", message="", user=current_user)


@app.route("/create", methods=['post', 'get'])
@login_required
def create():
    if request.method == 'POST':
        country_name = request.form.get('country_name')
        towns_names = [
            request.form.get('t1_name'), request.form.get('t2_name'),
            request.form.get('t3_name'), request.form.get('t4_name')
        ]
        if len(set(towns_names)) != 4:
            return render_template("country_country.html", message="Ошибка! Названия городов повторяются",
                                   user=current_user)


        perk = request.form.get('perk')

        lobby_name = request.form.get('lobby_name')
        lobby = Lobby.query.filter_by(title=lobby_name).first()

        if lobby is None:
            return render_template("country_country.html", message="Ошибка! Лобби с таким названием не существует",
                                   user=current_user)
        if lobby.password != request.form.get('lobby_password'):
            return render_template("country_country.html", message="Ошибка! Неверный пароль от лобби", user=current_user)
        if lobby.player_count == len(LobbyPlayer.query.filter_by(lobby_id=lobby.id).all()):
            return render_template("country_country.html", message="Ошибка! Это лобби уже заполнено", user=current_user)

        country_name_in_lobby = [
            country.country_name for country in LobbyPlayer.query.filter_by(lobby_id=lobby.id).all()
        ]
        if country_name in country_name_in_lobby:
            message = "Ошибка! Название страны уже занято!"
            return render_template("country_country.html", message=message, user=current_user)

        new_player = LobbyPlayer(lobby_id=lobby.id, country_name=country_name, perk=perk)

        db.session.add(new_player)
        db.session.flush()

        town_names_in_lobby = []
        for player in LobbyPlayer.query.filter_by(lobby_id=lobby.id).all():
            t = Town.query.filter_by(country_id=player.id).all()
            names = [town.name for town in t]
            for name in names:
                town_names_in_lobby.append(name)

        for name in towns_names:
            if name in town_names_in_lobby:
                db.session.rollback()
                return render_template("country_country.html", message="Ошибка! Название города/городов занято",
                                       user=current_user)

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

        return redirect(url_for("play", country_id=new_player.id))

    return render_template("country_country.html", message="", user=current_user)


@app.route("/end", methods=['POST', 'GET'])
@login_required
def end():
    players = LobbyPlayer.query.filter_by(final_id=current_user.last_game_id)

    players = sorted(players, key=lambda p: p.get_quality(), reverse=True)

    return render_template(
        "end_game.html",
        db=db, LobbyPlayer=LobbyPlayer,
        Lobby=Lobby, user=current_user,
        players=players, enumerate=enumerate
                           )


@app.route("/play/<country_id>", methods=['POST', 'GET'])
@login_required
def play(country_id):
    if current_user.current_country_id is None:
        if current_user.last_game_id is not None:
            return redirect(url_for("end"))
        else:
            return redirect(url_for("main"))

    if current_user.current_country_id is not int(country_id) \
            and current_user.role != "admin":
        return redirect(url_for("play", country_id=current_user.current_country_id))

    player = LobbyPlayer.query.filter_by(id=country_id).first()
    towns = Town.query.filter_by(country_id=country_id).all()
    lobby = Lobby.query.filter_by(id=player.lobby_id).first()
    if request.method == 'POST':
        # улучшения
        if request.form.get("upg"):
            upg_t = Town.query.filter_by(id=request.form.get(f"upg")).first()

            if player.money >= player.upg_cost and upg_t.quality > 0:
                if player.perk == "Нетерпеливый":
                    upg_t.quality += player.upg_power
                else:
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

                if player.perk == "Нетерпеливый":
                    shld_t.shield = 1
                else:
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
                player.money -= player.shield_cost * 3
                db.session.add(shld_t)
                db.session.add(player)
                db.session.commit()

        if request.form.get("nuke"):
            if player.money >= player.nuke_cost and player.nuke == "Нет" and \
                    player.nuke_next == "Не будет" and player.perk != "Пацифист":

                if player.perk == "Нетерпеливый":
                    player.nuke = "Есть"
                else:
                    player.nuke_next = "Будет"
                player.money -= player.nuke_cost
                db.session.add(player)
                db.session.commit()

        if request.form.get("bomb"):
            if player.money >= player.bombs_cost and player.nuke == "Есть":
                if player.perk == "Нетерпеливый":
                    player.bombs_count += 1
                else:
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
                if p.is_ready == 0 and p.get_quality() != 0:
                    all_ready = False
                    break
            if all_ready:
                lobby.round()
                if lobby.end_round <= lobby.round_num - 1:
                    player.game_end(lobby.final_id)
                    db.session.add(player)
                    db.session.commit()
                    all_end = True
                    for p in LobbyPlayer.query.filter_by(lobby_id=player.lobby_id).all():
                        if p.final_id is None:
                            all_end = False
                            break
                    if all_end:

                        db.session.delete(lobby)
                        db.session.commit()
                        return redirect(url_for("end"))

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

                if player.perk == "Нетерпеливый":
                    if target.shield > 0:
                        target.shield -= 1
                    else:
                        target.shield = 0
                        target.shield_next = 0
                        target.quality = 0
                        target.quality_next = 0
                else:

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
        db=db, towns=towns, player=player,
        LobbyPlayer=LobbyPlayer, Town=Town,
        Lobby=Lobby, str=str, len=len,
        user=current_user
    )


@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == "POST":
        password = request.form.get("user_password")
        name = request.form.get("user_name")
        target_user = Users.query.filter_by(name=name).first()
        if not target_user:
            return render_template("login.html", user=current_user, message="Ошибка! Такого пользователя нет")
        elif target_user.password == password:
            login_user(target_user)
            return redirect(url_for("main"))
        else:
            return render_template("login.html", user=current_user, message="Ошибка! mesНеверный пароль")

    return render_template("login.html", user=current_user)


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
            return render_template("register.html", message="Ошибка! Пользователь с таким именем уже есть", user=current_user)
        login_user(new_user)
        return redirect(url_for("main"))
    return render_template("register.html", message="", user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main'))


@app.route("/", methods=['post', 'get'])
def main():
    return render_template("main.html", user=current_user)


if __name__ == "__main__":
    app.run(debug=True)
