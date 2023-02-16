class Town:
    def __init__(self, name, is_capital=False):
        self.name = name

        if is_capital:
            self.quality = 75
        else:
            self.quality = 50

        self.quality_next = 0

        self.shield = False
        self.shield_next = False


class Player:
    def __init__(self, country_name, towns_names, perk):
        self.country_name = country_name
        self.towns = (
            Town(towns_names[0], is_capital=True),
            Town(towns_names[1]),
            Town(towns_names[2]),
            Town(towns_names[3])
        )
        self.perk = perk

        self.money = 1000

        self.nuke = False
        self.nuke_next = False

        self.bombs_count = 0
        self.bombs_count_next = 0

        self.sanctions = []
        self.sanctions_next = []

    def money_next(self):
        sum_quality = 0
        for i in self.towns:
            sum_quality += i.quality
            
        return sum_quality
