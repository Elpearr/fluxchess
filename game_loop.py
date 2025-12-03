

# Holds everything for game logic and PyGame


# Import everything

import pygame
import chess

from ui import (
    load_images,
    draw_board,
    get_square_from_mouse,
    show_text,
    WIDTH,
    HEIGHT,
    FPS,
    MoveAnimator,
)
from export_game_record import export_game_record


class GameState:
    # Bundling these all together into one class cuz it's easier

    def __init__(self, human_white: bool):
        self.board = chess.Board()      # fresh board
        self.human_white = human_white  # white or black
        self.selected_square = None     # stores which square the player clicks first; or none
        self.legal_targets = []         # list of all legal moves from selected piece
        self.result = None              # game result
        self.last_move_delta = None     # centipawn evaluation difference for the last human move
        self.ai_previews = None         # holds ai “preview” moves and their scores
        self.move_history = []          # list of all chess.Move objects played in the game


def create_initial_state(human_white: bool) -> GameState:       # constructs and returns a new GameState with given human colour
    return GameState(human_white=human_white)


def reset_game(state, human_white, profile, engine, animator):

    # Reset board + UI + evaluation state for a fresh game
    state.board.reset()
    state.human_white = human_white
    state.selected_square = None
    state.legal_targets = []
    state.result = None
    state.last_move_delta = None
    state.ai_previews = None
    state.move_history = []             
    animator.animations = []        # clear all

    engine.set_strength(profile.target_elo)     # reconfigure the engine difficulty based on the current target_elo from the profile; after adaptation from previous games


def handle_human_input(event, state, profile, engine, animator):
    
    # Process mouse clicks while the game is active

    if event.type == pygame.MOUSEBUTTONDOWN and not state.board.is_game_over():
        sq = get_square_from_mouse(event.pos)       # convert mouse xy to board positions

        # First click: select a piece
        if state.selected_square is None:
            piece = state.board.piece_at(sq)       # get whatever piece is here
            if piece and piece.color == (state.board.turn == chess.WHITE):  # is a piece and right colour? pass
                state.selected_square = sq  
                state.legal_targets = [         # make list of legal moves for the selected piece to make
                    m.to_square for m in state.board.legal_moves
                    if m.from_square == sq
                ]

        # Second click: try to make a move
        else:
            move = chess.Move(state.selected_square, sq)    # make chess.move object from start to this square
            if move in state.board.legal_moves:             # as long as it's valid
                move_san = state.board.san(move)            # turn move into SAN format for the log

                # Evaluate human move
                delta_cp = engine.evaluate_move(state.board, move)  # query engine about the move and board and return the centipawn value
                state.last_move_delta = delta_cp                    # store for the HUD

                if delta_cp is not None:                            # if engine gave an evaluation then adjust the ELO midgame based on delta
                    profile.adjust_midgame(delta_cp)
                    engine.set_strength(profile.target_elo)         # update engine
                    print(f"[HUMAN] {move_san} dcp={delta_cp:+} new Elo={profile.target_elo}")      # print log
                else:
                    print(f"[HUMAN] {move_san} (no eval) Elo={profile.target_elo}")

                state.board.push(move)          # make move (internally)
                state.move_history.append(move)     # log
                animator.start(move.from_square, move.to_square)    # make move (animation)

                state.selected_square = None    
                state.legal_targets = []
                state.ai_previews = None    # reset

            else:
                # Illegal move — clear selection
                state.selected_square = None
                state.legal_targets = []


def maybe_handle_ai_move(state, profile, engine, animator):
    # Handle AI previews and AI move execution.
    if state.board.is_game_over():  # skip if game over
        return

    ai_color = chess.BLACK if state.human_white else chess.WHITE    # which colour for ai

    # If it's not AI's turn, exit
    if state.board.turn != ai_color:
        return

    # First frame of AI turn → show preview arrows; waits a bit to let player see arrows before move
    if state.ai_previews is None:
        state.ai_previews = engine.preview_moves(state.board, profile.target_elo, pv_count=3)
        return

    # Next frame ->  AI actually makes its move
    move = engine.get_move(state.board, profile.target_elo)
    move_san = state.board.san(move)    # SAN for log
    state.board.push(move)              # make move (internal)
    state.move_history.append(move)     # add to log
    animator.start(move.from_square, move.to_square)    # make animation move

    # Pull cp value from previews if available
    cp_hint = None
    if state.ai_previews:       # skips if none for some reason
        for mv, cp in state.ai_previews:        # for every candidate move from previews compared to Centipawn score
            if mv == move:                      # then compares this move to the actual chosen move     (these are both chess.move objects ∴ comparable)
                cp_hint = cp                    # if it finds the same move platyed, it grabs its CP score and stops 
                break

    if cp_hint is not None:         
        print(f"[AI]    {move_san} at Elo {profile.target_elo} (cp {cp_hint:+})")
    else:
        print(f"[AI]    {move_san} at Elo {profile.target_elo}")    # if the preview moves wasnt the actual move

    state.ai_previews = None    # reset previews


def handle_game_over(state, profile, engine, args, animator):
    # Apply scoring, adapt profile, and export game record.

    if not state.board.is_game_over() or state.result is not None:  # ignore until game over
        return

    outcome = state.board.outcome()     

    # Convert game outcome into a numeric score for player
    if outcome.winner is None:
        score = 0.5
    elif outcome.winner == (chess.WHITE if state.human_white else chess.BLACK):
        score = 1.0
    else:
        score = 0.0

    profile.record_result(score)        # record score
    profile.adapt()                     # adapt elo / difficulty based on the accumulated info
    profile.save(args.persist)          # save profile to disc at args.persist

    state.result = score                # store score in state.result so the handler doesnt run again for the same game
    state.ai_previews = None            # reset
    state.selected_square = None        # reset
    state.legal_targets = []            # reset
    animator.animations = []            # reset
    engine.set_strength(profile.target_elo)     # update difficulty again so next game is at new elo

    try:                                                # try export results to .jsonl with game history, move history, game outcome, and final elo
        export_game_record(args.games_json, state.move_history, outcome, profile.target_elo)
    except Exception as e:
        print(f"[WARN] Failed to save game record: {e}")    # in case error


def draw_hud(win, state, profile):
    # Draw HUD text overlay
    show_text(win, f"AI Elo: {profile.target_elo}", 10)                                     # draw all of these with offset "x"
    show_text(win, f"You are: {'White' if state.human_white else 'Black'}", 30)
    show_text(win, f"Results: {profile.results}", 50)

    if state.last_move_delta is not None:
        show_text(win, f"Last move delta (cp): {state.last_move_delta:+}", 70)

    if state.board.is_game_over():
        show_text(win, "Game Over - Press R to restart (C to swap colours)", 85, (255, 100, 100))


def run_game_loop(profile, engine, args):
    # Runs PyGame loop until close
    pygame.init()
    win = pygame.display.set_mode((WIDTH, HEIGHT + 120))    # draw main window + offset for the text HUD
    pygame.display.set_caption("FXCHESS")

    load_images()       # from ui.py
    clock = pygame.time.Clock()     # for regulating fps
    animator = MoveAnimator(duration_ms=200)    # all anims have duration of 200ms

    state = create_initial_state(human_white=(args.human_color == "white"))     # make new game state w/ arguments from command prompt argument
    engine.set_strength(profile.target_elo)     # set elo to current profile's target elo

    running = True
    try:            # using try so cleanup is better
        while running:
            clock.tick(FPS)

            for event in pygame.event.get():    # get all pygame events and iterate over them
                if event.type == pygame.QUIT:   # close window =  stop
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:    # esc = stop
                        running = False
                    elif event.key == pygame.K_r:       # r = reset
                        reset_game(state, state.human_white, profile, engine, animator)
                    elif event.key == pygame.K_c:       # c = colour change
                        reset_game(state, not state.human_white, profile, engine, animator)

                else:
                    handle_human_input(event, state, profile, engine, animator) # if anything else it'll still try; includes mouse input

            maybe_handle_ai_move(state, profile, engine, animator)          # let ai think / preview
            handle_game_over(state, profile, engine, args, animator)        # if game is over start logging

            win.fill((50, 50, 50))      # reset window
            draw_board(
                win,
                state.board,
                state.selected_square,
                state.legal_targets,
                animator=animator,
                ai_arrows=state.ai_previews,        # draw everything
            )

            draw_hud(win, state, profile)   # draw hud text
            pygame.display.flip()           # update actual visible window

    finally:            # no matter how loop is exited; still exits in same process
        engine.close()      
        pygame.quit()           # close both of these cleanly