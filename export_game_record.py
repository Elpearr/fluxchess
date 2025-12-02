import json
from datetime import datetime
import chess
import chess.pgn

# Write single game record; SAN list + PGN, to .jsonl file
# Write to existing directory with the games saved moves in memory, alongside outcome and final ELO
def export_game_record(path, moves, outcome, ai_final_elo):
    try:
        # Convert moves to SAN
        moves_san = []
        tmp_board = chess.Board()  # fresh board

        for mv in moves:
            # Convert move -> SAN based on current board state
            moves_san.append(tmp_board.san(mv))
            tmp_board.push(mv)

        # --- Build PGN using python-chess ---
        game = chess.pgn.Game()  # fresh PGN object
        game.headers["RESULT"] = outcome.result()

        node = game       # pointer to current PGN node
        tmp_board = chess.Board()  # fresh board again for PGN structure

        for mv in moves:
            # Append move into PGN's mainline
            node = node.add_main_variation(mv)
            tmp_board.push(mv)

        pgn_str = str(game)  # convert entire PGN object to raw PGN text

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
