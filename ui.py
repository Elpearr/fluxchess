# DEFINITIONS

import pygame
import chess
import os
from utils import PIECE_DIR, clamp

WIDTH, HEIGHT = 640, 640
SQUARE_SIZE = WIDTH // 8
FPS = 30
COLORS = [(240, 217, 181), (181, 136, 99)]
PIECE_IMAGES = {}
HIGHLIGHT_COLOR = (200, 80, 80, 100)
TARGET_COLOR = (80, 180, 120, 120)
ARROW_COLOR = (70, 140, 220, 140)


# TWEENING ANIMATIONS

def ease_out_quad(t):
    # quadratic easing curve
    return 1 - (1 - t) * (1 - t)

def lerp(a, b, t):      # linear interpolation
    return a + (b - a) * t

class MoveAnimator:
    # smooooth
    def __init__(self, duration_ms=200):
        self.duration_ms = duration_ms
        self.animations = []  # list of dicts

    def start(self, from_sq, to_sq):
        # called when move made
        now = pygame.time.get_ticks()

        from_file = chess.square_file(from_sq)
        from_rank = chess.square_rank(from_sq)
        to_file   = chess.square_file(to_sq)
        to_rank   = chess.square_rank(to_sq)

        start_x = from_file * SQUARE_SIZE
        start_y = (7 - from_rank) * SQUARE_SIZE
        end_x   = to_file * SQUARE_SIZE
        end_y   = (7 - to_rank) * SQUARE_SIZE

        self.animations.append({
            "to_sq": to_sq,
            "start_x": start_x,
            "start_y": start_y,
            "end_x": end_x,
            "end_y": end_y,
            "start_time": now,
        })

    def is_animating(self):
        return bool(self.animations)

    def get_position(self, sq, default_topleft):
        """
        Given a board square and its default (x, y) for drawing,
        return the tweened position if this square is currently animating.
        """
        if not self.animations:
            return default_topleft

        now = pygame.time.get_ticks()
        finished = []
        x, y = default_topleft

        for anim in self.animations:
            # Clean up finished animations but still return final pos on this frame
            elapsed = now - anim["start_time"]
            t = elapsed / float(self.duration_ms)

            if t >= 1.0:
                finished.append(anim)
                if sq == anim["to_sq"]:
                    x, y = anim["end_x"], anim["end_y"]
                continue

            if sq == anim["to_sq"]:
                t = max(0.0, min(1.0, t))
                eased = ease_out_quad(t)
                x = lerp(anim["start_x"], anim["end_x"], eased)
                y = lerp(anim["start_y"], anim["end_y"], eased)

        # remove completed animations
        for anim in finished:
            if anim in self.animations:
                self.animations.remove(anim)

        return int(x), int(y)






def load_images():
    pieces = ['P','N','B','R','Q','K']
    for piece in pieces:
        for color in ['w','b']:
            path = os.path.join(PIECE_DIR, f"{color}{piece}.png")
            if os.path.exists(path):
                PIECE_IMAGES[color+piece] = pygame.transform.smoothscale(
                    pygame.image.load(path),
                    (SQUARE_SIZE, SQUARE_SIZE)
                )

def square_center(sq):
    file = chess.square_file(sq)
    rank = chess.square_rank(sq)
    x = file * SQUARE_SIZE + SQUARE_SIZE // 2
    y = (7 - rank) * SQUARE_SIZE + SQUARE_SIZE // 2
    return x, y

def draw_arrows(win, arrows):
    """Draw translucent arrows for candidate engine moves: arrows is list of (move, cp_score)."""
    if not arrows:
        return
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for idx, (move, cp) in enumerate(arrows):
        start = square_center(move.from_square)
        end = square_center(move.to_square)
        intensity = max(0.4, 1.0 - (idx * 0.2))
        color = (
            int(ARROW_COLOR[0] * intensity),
            int(ARROW_COLOR[1] * intensity),
            int(ARROW_COLOR[2] * intensity),
            ARROW_COLOR[3]
        )
        pygame.draw.line(overlay, color, start, end, width=6)
        head_len = 14
        head_width = 8
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = max((dx*dx + dy*dy) ** 0.5, 1)
        ux, uy = dx / length, dy / length
        left = (end[0] - ux * head_len + uy * head_width, end[1] - uy * head_len - ux * head_width)
        right = (end[0] - ux * head_len - uy * head_width, end[1] - uy * head_len + ux * head_width)
        pygame.draw.polygon(overlay, color, [end, left, right])
    win.blit(overlay, (0, 0))

def draw_board(win, board, selected_square=None, legal_targets=None, animator=None, ai_arrows=None):
    # Draw the board, pieces, and simple highlights for selection and legal moves.
    legal_targets = legal_targets or []
    for r in range(8):
        for f in range(8):
            color = COLORS[(r+f)%2]
            rect = pygame.Rect(f*SQUARE_SIZE, r*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            pygame.draw.rect(win, color, rect)

            sq = chess.square(f, 7-r)

            if selected_square == sq:
                s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                s.fill(HIGHLIGHT_COLOR)
                win.blit(s, rect)

            if sq in legal_targets:
                s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                s.fill(TARGET_COLOR)
                win.blit(s, rect)

            piece = board.piece_at(sq)
            if piece:
                img = PIECE_IMAGES.get(('w' if piece.color else 'b') + piece.symbol().upper())
                if img:
                    if animator is not None:
                        # use tweened pos if this square is animating
                        pos = animator.get_position(sq, rect.topleft)
                        win.blit(img, pos)
                    else:
                        win.blit(img, rect)
    draw_arrows(win, ai_arrows or [])

def get_square_from_mouse(pos):
    x,y = pos
    return chess.square(x//SQUARE_SIZE, 7-(y//SQUARE_SIZE))

def show_text(win, text, y_offset=10, color=(255,255,255), font_size=24):
    font = pygame.font.SysFont("arial", font_size)
    surf = font.render(text, True, color)
    win.blit(surf, (10, HEIGHT + y_offset))
