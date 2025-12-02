



"""
python main.py --engine "C:\\Users\\imael\\Documents\\YSTE-26\\FXCHESS-GAMMA - EXE TEST\\dragon-64bit-avx2.exe"
"""


# REMEMBER:
# SAN is Standard Algebraic Notation
# CP is Centipawn; helps evaluate whos winning (1/100 of a pawn)

import argparse
from player_profile import PlayerProfile
from engine_wrapper import EngineWrapper
from game_loop import run_game_loop   # ← now valid

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--persist", default="player_profile.json")
    ap.add_argument("--time", type=int, default=200)
    ap.add_argument("--games-json", default="game_history.jsonl")
    ap.add_argument("--human-color", choices=["white", "black"], default="white")
    ap.add_argument(
        "--engine",
        default=r"C:\Users\imael\Documents\FXCHESS-GAMMA\dragon-64bit-avx2.exe",
        help="Path to the chess engine executable",
    )
    args = ap.parse_args()

    profile = PlayerProfile.load(args.persist)
    engine = EngineWrapper(args.engine, args.time)

    run_game_loop(profile, engine, args)

if __name__ == "__main__":
    main()