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
        """
        try:
            pov_color = board.turn  # color about to move (the human)
            limit = chess.engine.Limit(time=max(0.1, self.movetime_ms / 1000))

            info_before = self.engine.analyse(board, limit)
            score_before = info_before.get("score")
            if score_before is None:
                return None

            before_cp = score_before.pov(pov_color).score(mate_score=100000)
            if before_cp is None:
                return None

            board.push(move)
            info_after = self.engine.analyse(board, limit)
            board.pop()

            score_after = info_after.get("score")
            if score_after is None:
                return None

            after_cp = score_after.pov(pov_color).score(mate_score=100000)
            if after_cp is None:
                return None

            return after_cp - before_cp
        except Exception as e:
            print(f"[WARN] Failed to evaluate move: {e}")
            return None

    def close(self):
        self.engine.quit()
