import os
import json
from utils import clamp

# player profiling w/ json

class PlayerProfile:
    def __init__(self, name="player", target_elo=900, window=8, k=50, elo_min=400, elo_max=3200, midgame_k=10):

        # set up the players info and default values; idk @dataclass yet

        self.name = name
        self.target_elo = target_elo
        self.results = []        # list of recent game results
        self.window = window     # how many recent results to remember
        self.k = k               # how fast elo can change on game result
        self.midgame_k = midgame_k  # how fast elo can change per move
        self.elo_min = elo_min   # minimum elo
        self.elo_max = elo_max   # maximum elo

    def record_result(self, score):
        # add new game resulst; 1 = win, 0.5 = draw, 0 = loss
        self.results.append(score)

        # only keep recent resulsts if too many
        if len(self.results) > self.window:
            self.results = self.results[-self.window:]

    def adapt(self):
        # update the elo based on average performance.
        if not self.results:
            return

        mean_score = sum(self.results) / len(self.results) # mean average
        performance = mean_score - 0.5  # +ve if good, -ve if bad
        change = round(self.k * performance)

        # update elo & stay within limits
        new_elo = self.target_elo + change
        self.target_elo = clamp(new_elo, self.elo_min, self.elo_max)

    def adjust_midgame(self, delta_cp):
        #   Adjust Elo mid-game based on the centipawn swing of the last move.
        #   Positive delta means the player's move improved their position.
        
        if delta_cp is None:
            return

        # Each ~80cp swing nudges Elo by midgame_k; cap to avoid wild jumps.
        step = clamp(int(delta_cp / 80), -2, 2)
        if step == 0:
            return

        new_elo = self.target_elo + (step * self.midgame_k)
        self.target_elo = clamp(new_elo, self.elo_min, self.elo_max)

    def save(self, path):
        # save data to json yay
        data = {
            "name": self.name,
            "target_elo": self.target_elo,
            "results": self.results,
            "window": self.window,
            "k": self.k,
            "elo_min": self.elo_min,
            "elo_max": self.elo_max,
            "midgame_k": self.midgame_k,
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load(path):
        # load data or make new if none
        if not os.path.exists(path):
            return PlayerProfile()  # make new w/ defaults

        with open(path, "r") as f:
            data = json.load(f)

        # create player profile with loaded data
        player = PlayerProfile()
        player.name = data.get("name", "player")
        player.target_elo = data.get("target_elo", 900)
        player.results = data.get("results", [])
        player.window = data.get("window", 8)
        player.k = data.get("k", 50)
        player.elo_min = data.get("elo_min", 400)
        player.elo_max = data.get("elo_max", 3200)
        player.midgame_k = data.get("midgame_k", 10)
        return player
