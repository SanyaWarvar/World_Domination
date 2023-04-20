from config import db, login_manager
from flask_login import UserMixin


class Lobby(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(20), unique=True, nullable=True)
    eco = db.Column(db.Float)
    eco_next = db.Column(db.Float)
    round_num = db.Column(db.Integer)

    def __init__(self, title):
        self.eco = 90
        self.eco_next = 0
        self.title = title

    def round(self):
        self.eco += self.eco_next
        self.eco_next = 0

        for player in LobbyPlayer.query.filter_by(lobby_id=self.id).all():
            player.is_ready = False
            player.atk = ""
            player.sy = ""
            player.sanctions += player.sanctions_next
            player.sanctions_next = ""
            player.money += round(
                player.money_mltp * player.get_quality() * (1 - 0.1 * (player.sanctions.count("|")//2))
            )

            if player.nuke_next == "Будет":
                player.nuke_next = "Не будет"
                player.nuke = "Есть"

            player.bombs_count += player.bombs_count_next
            player.bombs_count_next = 0
            db.session.add(player)
            db.session.commit()

            for t in Town.query.filter_by(country_id=player.id).all():
                t.quality += t.quality_next
                t.quality_next = 0

                if t.shield_next != 0:
                    t.shield = t.shield_next
                    t.shield_next = 0

                t.shield -= t.atk_count
                t.atk_count = 0

                if t.shield < 0:
                    t.shield = 0
                    t.quality = 0
                    marauder = LobbyPlayer.query.filter_by(lobby_id=self.id, perk="Мародер").all()
                    for p in marauder:
                        p.money += 75
                        p.money_mltp += 0.05
                        p.money_mltp = min(p.money_mltp, 4)
                        db.session.add(p)
                        db.session.commit()

                db.session.add(t)
                db.session.commit()


class LobbyPlayer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lobby_id = db.Column(db.Integer)
    is_ready = db.Column(db.Boolean)

    atk = db.Column(db.String(100))

    country_name = db.Column(db.String(20))

    perk = db.Column(db.String(20))

    money = db.Column(db.Integer)
    money_mltp = db.Column(db.Float)

    nuke = db.Column(db.String(4))
    nuke_next = db.Column(db.String(8))

    bombs_count = db.Column(db.Integer)
    bombs_count_next = db.Column(db.Integer)

    sanctions = db.Column(db.String(100))
    sanctions_next = db.Column(db.String(100))
    spy = db.Column(db.String(100))

    bombs_cost = db.Column(db.Integer)
    shield_cost = db.Column(db.Integer)
    nuke_cost = db.Column(db.Integer)
    upg_cost = db.Column(db.Integer)
    spy_cost = db.Column(db.Integer)
    upg_power = db.Column(db.Integer)
    sanct_power_self = db.Column(db.Integer)
    sanct_power_other = db.Column(db.Integer)
    money_mltp_power = db.Column(db.Integer)

    def __init__(self, lobby_id, country_name, perk):
        self.lobby_id = lobby_id
        self.country_name = country_name
        self.is_ready = False
        self.atk = ""

        self.perk = perk

        self.money = 1000
        self.money_next = 225
        self.money_mltp = 1

        self.nuke = "Нет"
        self.nuke_next = "Не будет"

        self.bombs_count = 0
        self.bombs_count_next = 0

        self.sanctions = ""
        self.sanctions_next = ""

        self.spy = ""

        self.bombs_cost = 150
        self.shield_cost = 300
        self.nuke_cost = 500
        self.upg_cost = 150
        self.spy_cost = 200

        self.upg_power = 25
        self.money_mltp_power = 0.2
        self.sanct_power_self = 0.1
        self.sanct_power_other = 0.1

    def perk_change(self):
        if self.perk == "Пацифист":
            self.shield_cost = 250
            for t in Town.query.filter_by(country_id=self.id):
                t.quality += 25
                db.session.add(t)
                db.session.commit()

        elif self.perk == "Житель пустоши":
            self.bombs_cost = 100
            self.nuke_cost = 400
            self.upg_power = 15
            self.money_mltp_power = 0.15

        elif self.perk == "Нетерпеливый":
            self.money = 500
            self.money_mltp = 0.5

        elif self.perk == "Дед Инсайд":
            self.sanct_power_self = 0.05

            for t in Town.query.filter_by(country_id=self.id).all():
                print(t.name, t.quality)
                t.quality -= 15
                print(t.name, t.quality)
                db.session.add(t)
                db.session.commit()

        elif self.perk == "Берсерк":
            self.bombs_cost = 200

        elif self.perk == "Золотой телец":
            self.money_mltp_power += 0.25

        elif self.perk == "Друид":
            self.bombs_cost = 175
            self.nuke = 550

        elif self.perk == "Мародер":
            self.sanct_power_self = 0.15

        elif self.perk == "Джимми Нейтрон":
            self.sanct_power_other = 0

    def get_quality(self):
        towns = Town.query.filter_by(country_id=self.id).all()
        s = 0
        for i in towns:
            s += i.quality
        return s

    def money_next(self):
        towns = Town.query.filter_by(country_id=self.id).all()
        next_quality = 0
        for t in towns:
            next_quality += t.quality
        return round((self.get_quality() + next_quality) * self.money_mltp)


class Town(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    country_id = db.Column(db.Integer)
    name = db.Column(db.String(20))
    quality = db.Column(db.Integer)
    quality_next = db.Column(db.Integer)
    atk_count = db.Column(db.Integer)
    shield = db.Column(db.Integer)
    shield_next = db.Column(db.Integer)
    upg_count = db.Column(db.Integer)

    def __init__(self, country_id, name, quality):
        self.country_id = country_id
        self.name = name

        self.quality = quality

        self.quality_next = 0

        self.atk_count = 0
        self.shield = 0
        self.shield_next = 0
        self.upg_count = 0

    def under_attack(self):
        self.atk_count += 1


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    current_country_id = db.Column(db.Integer)
    name = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(20))
    status = db.Column(db.Boolean)

    def __init__(self, name, password):
        self.name = name
        self.password = password
        self.role = "user"

    def check_password(self, password):
        return password == self.password


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(Users).get(user_id)
