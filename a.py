#!/usr/bin/env python3
"""
Adaptive Stockfish Opponent — PyGame Version (Interactive UI)

for startup:

python a.py --engine ./stockfish.exe
"""

import argparse
import os
import json
import chess
import chess.engine
import pygame
from dataclasses import dataclass, asdict, field
from typing import List

ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
PIECE_DIR = os.path.join(ASSET_DIR, "pieces")

# -------------------
# Utility
# -------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

# -------------------
# Player profile
# -------------------

@dataclass
class PlayerProfile:
    name: str = "player"
    target_elo: int = 1320  # ← was 1200
    results: List[float] = field(default_factory=list)
    window: int = 8
    k: int = 50
    elo_min: int = 1320     # ← was 800
    elo_max: int = 3190     # ← was 2500

    def record_result(self, score: float) -> None:
        self.results.append(score)
        if len(self.results) > self.window:
            self.results = self.results[-self.window:]

    def adapt(self) -> None:
        """Update target_elo based on recent results."""
        if not self.results:
            return
        mean_score = sum(self.results) / len(self.results)
        performance = mean_score - 0.5
        delta = int(round(self.k * performance))
        new_elo = self.target_elo + delta
        self.target_elo = clamp(new_elo, self.elo_min, self.elo_max)

    @classmethod
    def load(cls, path: str):
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**data)

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

# -------------------
# Stockfish wrapper
# -------------------

class EngineWrapper:
    def __init__(self, path, movetime_ms=200):
        self.engine = chess.engine.SimpleEngine.popen_uci(path)
        self.movetime_ms = movetime_ms
        self._supports_limit_strength = "UCI_LimitStrength" in self.engine.options
        self._supports_elo = "UCI_Elo" in self.engine.options
        self._supports_skill = "Skill Level" in self.engine.options

    def set_strength(self, target_elo):
        """Configure Stockfish difficulty safely."""
        try:
            if self._supports_limit_strength and self._supports_elo:
                safe_elo = max(1320, target_elo)
                self.engine.configure({
                    "UCI_LimitStrength": True,
                    "UCI_Elo": safe_elo
                })
            elif self._supports_skill:
                # Fallback for engines without UCI_Elo
                skill = int(round((target_elo - 800) / (2500 - 800) * 20))
                self.engine.configure({"Skill Level": max(0, min(20, skill))})
        except Exception as e:
            print(f"[WARN] Failed to set strength: {e}")

    def get_move(self, board):
        result = self.engine.play(board, chess.engine.Limit(time=self.movetime_ms / 1000))
        return result.move

    def close(self):
        self.engine.quit()

# -------------------
# PyGame setup
# -------------------

WIDTH, HEIGHT = 640, 640
SQUARE_SIZE = WIDTH // 8
FPS = 30

COLORS = [(240, 217, 181), (181, 136, 99)]  # light, dark
PIECE_IMAGES = {}


def load_images():
    pieces = ['P', 'N', 'B', 'R', 'Q', 'K']
    for piece in pieces:
        white_path = os.path.join(PIECE_DIR, f"w{piece}.png")
        black_path = os.path.join(PIECE_DIR, f"b{piece}.png")

        print("Loading images from:", PIECE_DIR)
        print("Files found:", os.listdir(PIECE_DIR))

        if os.path.exists(white_path):
            PIECE_IMAGES[piece] = pygame.transform.smoothscale(
                pygame.image.load(white_path),
                (SQUARE_SIZE, SQUARE_SIZE)
            )
        else:
            print(f"[WARN] Missing image: {white_path}")

        if os.path.exists(black_path):
            PIECE_IMAGES[piece.lower()] = pygame.transform.smoothscale(
                pygame.image.load(black_path),
                (SQUARE_SIZE, SQUARE_SIZE)
            )
        else:
            print(f"[WARN] Missing image: {black_path}")


def draw_board(win, board, selected_square=None):
    for rank in range(8):
        for file in range(8):
            color = COLORS[(rank + file) % 2]
            rect = pygame.Rect(file * SQUARE_SIZE, rank * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            pygame.draw.rect(win, color, rect)

            square = chess.square(file, 7 - rank)
            piece = board.piece_at(square)
            if piece:
                img = PIECE_IMAGES.get(piece.symbol())
                if img:
                    win.blit(img, rect)
                else:
                    font = pygame.font.SysFont("arial", 36, bold=True)
                    surf = font.render(piece.symbol(), True, (0,0,0))
                    win.blit(surf, rect)

    if selected_square is not None:
        r = 7 - chess.square_rank(selected_square)
        f = chess.square_file(selected_square)
        pygame.draw.rect(win, (0, 255, 0), (f*SQUARE_SIZE, r*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE), 3)

def get_square_from_mouse(pos):
    x, y = pos
    file = x // SQUARE_SIZE
    rank = 7 - (y // SQUARE_SIZE)
    return chess.square(file, rank)

def show_text(win, text, y_offset=10, color=(255,255,255), font_size=24):
    font = pygame.font.SysFont("arial", font_size)
    surf = font.render(text, True, color)
    win.blit(surf, (10, HEIGHT + y_offset))

# -------------------
# Main game loop
# -------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--engine', required=True)
    ap.add_argument('--persist', default='player_profile.json')
    ap.add_argument('--time', type=int, default=200)
    args = ap.parse_args()

    profile = PlayerProfile.load(args.persist) or PlayerProfile()
    engine = EngineWrapper(args.engine, args.time)

    pygame.init()
    win = pygame.display.set_mode((WIDTH, HEIGHT + 80))
    pygame.display.set_caption("Adaptive Stockfish Opponent")
    clock = pygame.time.Clock()
    load_images()

    board = chess.Board()
    human_white = True
    engine.set_strength(profile.target_elo)
    selected_square = None
    running = True
    result = None

    try:
        while running:
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    board.reset()
                    engine.set_strength(profile.target_elo)
                    selected_square = None
                    result = None
                elif event.type == pygame.MOUSEBUTTONDOWN and not board.is_game_over():
                    square = get_square_from_mouse(event.pos)
                    if selected_square is None:
                        piece = board.piece_at(square)
                        if piece and piece.color == (board.turn == chess.WHITE):
                            selected_square = square
                    else:
                        move = chess.Move(selected_square, square)
                        if move in board.legal_moves:
                            board.push(move)
                            selected_square = None
                        else:
                            selected_square = None

            if not board.is_game_over() and board.turn != (chess.WHITE if human_white else chess.BLACK):
                move = engine.get_move(board)
                board.push(move)

            win.fill((50, 50, 50))
            draw_board(win, board, selected_square)

            if board.is_game_over() and result is None:
                outcome = board.outcome()
                if outcome.winner is None:
                    score = 0.5
                elif outcome.winner == (chess.WHITE if human_white else chess.BLACK):
                    score = 1.0
                else:
                    score = 0.0
                profile.record_result(score)
                profile.adapt()
                profile.save(args.persist)
                result = score
                engine.set_strength(profile.target_elo)

            show_text(win, f"AI Elo: {profile.target_elo}", 10)
            show_text(win, f"Results: {profile.results}", 35)
            if board.is_game_over():
                show_text(win, "Game Over — Press R to restart", 60, (255,100,100))

            pygame.display.flip()

    finally:
        engine.close()
        pygame.quit()

if __name__ == '__main__':
    main()
