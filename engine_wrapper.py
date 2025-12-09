import random
import chess.engine
from utils import clamp

class EngineWrapper:
    def __init__(self, path, movetime_ms=200):
        self.engine = chess.engine.SimpleEngine.popen_uci(path)
        self.movetime_ms = movetime_ms
        self._supports_limit_strength = "UCI_LimitStrength" in self.engine.options
        self._supports_elo = "UCI_Elo" in self.engine.options
        self._supports_skill = "Skill Level" in self.engine.options

    def set_strength(self, target_elo):
        """Set engine difficulty based on target Elo."""
        try:
            if self._supports_limit_strength and self._supports_elo:
                self.engine.configure({
                    "UCI_LimitStrength": True,
                    "UCI_Elo": clamp(target_elo, 1320, 3200)
                })
            elif self._supports_skill:
                skill = int(round((target_elo - 400) / (3200 - 400) * 20))
                self.engine.configure({"Skill Level": clamp(skill, 0, 20)})
            else:
                print("[WARN] Engine does not support built-in strength control; using synthetic scaling.")
        except Exception as e:
            print(f"[WARN] Failed to set strength: {e}")

    def get_move(self, board, target_elo):
        base_time = max(0.05, (target_elo / 3200) * 1.5)
        think_time = base_time + random.uniform(0, 0.1)

        if target_elo < 1320:
            multipv_count = clamp(2 + (target_elo // 100), 1, 5)
            info = self.engine.analyse(board, chess.engine.Limit(time=think_time), multipv=multipv_count)
            moves = [i["pv"][0] for i in info if "pv" in i]
            if moves:
                if random.random() < 0.7:
                    return moves[0]
                else:
                    return random.choice(moves[1:])
        result = self.engine.play(board, chess.engine.Limit(time=think_time))
        return result.move

    def preview_moves(self, board, target_elo, pv_count=5):
        """
        Return a list of (move, cp_score) candidate lines for display.
        cp_score is from the side to move (AI) perspective.
        """
        try:
            limit_time = max(0.2, min(0.8, self.movetime_ms / 800.0))
            info = self.engine.analyse(
                board,
                chess.engine.Limit(time=limit_time),
                multipv=pv_count
            )
            previews = []
            for item in info:
                pv = item.get("pv")
                score = item.get("score")
                if not pv or not score:
                    continue
                move = pv[0]
                cp = score.pov(board.turn).score(mate_score=100000)
                if cp is None:
                    continue
                previews.append((move, cp))
            return previews[:pv_count]
        except Exception as e:
            print(f"[WARN] Failed to preview moves: {e}")
            return []

    def evaluate_move(self, board, move):
        """
        Estimate move quality in centipawns relative to the mover.
        Returns (after - before) cp; positive means the move improved the position.
        Uses board copies so we don't disturb the live state and keeps POV fixed.
        Removes tempo bias by evaluating "before" with a null move so both evals
        are from the position where the opponent is to move.
        """
        try:
            mover = board.turn  # color about to move
            limit = chess.engine.Limit(time=max(0.1, self.movetime_ms / 1000))

            # Work on copies to avoid touching the live board
            before_board = board.copy(stack=False)
            # Apply a null move so turn matches the "after" position (opponent to move)
            if before_board.is_check():
                # Avoid illegal null move; fall back to raw board
                pass
            else:
                before_board.push(chess.Move.null())
            after_board = board.copy(stack=False)
            after_board.push(move)

            def score_cp(b):
                info = self.engine.analyse(b, limit)
                sc = info.get("score")
                return None if sc is None else sc.pov(mover).score(mate_score=100000)

            before_cp = score_cp(before_board)
            after_cp = score_cp(after_board)
            if before_cp is None or after_cp is None:
                return None

            return after_cp - before_cp

        except Exception as e:
            print(f"[WARN] Failed to evaluate move: {e}")
            return None

    def close(self):
        self.engine.quit()
