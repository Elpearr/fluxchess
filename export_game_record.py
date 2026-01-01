import json
from datetime import datetime
import chess
import chess.pgn

# Write single game record; SAN list + PGN, to .jsonl file
# Write to existing directory with the games saved moves in memory, alongside outcome and final ELO
def _build_pgn(moves, result_str=None):
    # Build a PGN string from a list of chess.Move. Optionally set result header.
    game = chess.pgn.Game()
    if result_str:
        game.headers["RESULT"] = result_str

    node = game
    for mv in moves:
        node = node.add_main_variation(mv)

    return str(game)


def write_live_pgn(path, moves):
    # Overwrite a PGN file with the current game so far.
    try:
        pgn_str = _build_pgn(moves)
        with open(path, "w", encoding="utf-8") as f:
            f.write(pgn_str)
    except Exception as e:
        print(f"[WARN] Failed to write live PGN: {e}")


def export_game_record(path, moves, outcome, ai_final_elo, feedback=None):
    try:
        # Convert moves to SAN
        moves_san = []
        tmp_board = chess.Board()  # fresh board

        for mv in moves:
            # Convert move -> SAN based on current board state
            moves_san.append(tmp_board.san(mv))
            tmp_board.push(mv)

        # Build PGN using python-chess
        pgn_str = _build_pgn(moves, outcome.result())

        # Build JSON record for .jsonl logging 
        record = {
            "timestamp": datetime.now().isoformat(),
            "result": outcome.result(),
            "winner": (
                "white" if outcome.winner is chess.WHITE
                else "black" if outcome.winner is chess.BLACK
                else None
            ),
            "ai_final_elo": ai_final_elo,
            "moves_san": moves_san,
            "feedback": feedback if feedback is not None else [],
            "pgn": pgn_str
        }

        # Append new JSON line to file
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record))
            f.write("\n")

        print(f"[   NOTICE   ] Game saved record to {path}")

    except Exception as e:
        # catch anything that can break log
        print(f"[   ERROR    ] Failed to export game record: {e}")
