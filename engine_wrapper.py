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
    
    # More robust evaluation: - POV fixed (removes tempo bias) - clamps insane evals - smooths delta swings  - ignores small opening noise; gracias chatgpt
        try:
            mover = board.turn
            limit = chess.engine.Limit(time=max(0.1, self.movetime_ms / 1000))

            # ----- Build before/after boards -----
            before_board = board.copy(stack=False)
            if not before_board.is_check():
                before_board.push(chess.Move.null())

            after_board = board.copy(stack=False)
            after_board.push(move)

            def score_cp(b):
                try:
                    info = self.engine.analyse(b, limit)
                    sc = info.get("score")
                    if sc is None:
                        return None
                    cp = sc.pov(mover).score(mate_score=100000)
                    return cp
                except:
                    return None

            before_cp = score_cp(before_board)
            after_cp = score_cp(after_board)

            # ----- Basic sanity checks -----
            if before_cp is None or after_cp is None:
                return 0  # fallback neutral

            delta = after_cp - before_cp

            # absurd spikes → clamp
            if abs(delta) > 800:
                delta = 0

            # ----- Opening-phase dampening -----
            plies = board.fullmove_number * 2
            if mover == chess.BLACK:
                plies -= 1  # fix indexing

            if plies <= 14:  # opening ≈ first 7 moves each
                if abs(delta) < 40:
                    delta = 0

            # ----- Smoothing: EMA over last delta -----
            if not hasattr(self, "_prev_delta"):
                self._prev_delta = 0

            smoothed = 0.7 * delta + 0.3 * self._prev_delta
            self._prev_delta = smoothed

            return round(smoothed)

        except Exception as e:
            print(f"[WARN] Failed to evaluate move: {e}")
            return 0


    def close(self):
        self.engine.quit()
