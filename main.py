



r"""
python main.py --engine "C:\Users\imael\Documents\YSTE-26\FXCHESS-DELTA\dragon-64bit-avx2.exe"
"""


# REMEMBER:
# SAN is Standard Algebraic Notation
# CP is Centipawn; helps evaluate whos winning (1/100 of a pawn)

import argparse
from player_profile import PlayerProfile
from engine_wrapper import EngineWrapper
from game_loop import run_game_loop  
from utils import resource_path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--persist", default="player_profile.json")
    ap.add_argument("--time", type=int, default=200)
    ap.add_argument("--games-json", default="game_history.jsonl")
    ap.add_argument("--live-pgn", default="live_game.pgn", help="Continuously overwrite this PGN file with the current game (set to '' to disable).")
    ap.add_argument("--human-color", choices=["white", "black"], default="white")
    ap.add_argument(
        "--engine",
        default=resource_path("dragon-64bit-avx2.exe"),
        help="Path to the chess engine executable (defaults to bundled dragon-64bit-avx2.exe)",
    )
    args = ap.parse_args()

    if args.live_pgn == "":
        args.live_pgn = None

    profile = PlayerProfile.load(args.persist)
    engine = EngineWrapper(args.engine, args.time)

    run_game_loop(profile, engine, args)

if __name__ == "__main__":
    main()
