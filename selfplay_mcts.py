import itertools
import numpy as np
import random
import time

import coords
import go
from gtp_wrapper import MCTSPlayer

SIMULTANEOUS_LEAVES = 8

def play(network, readouts, resign_threshold, verbosity=0):
    ''' Plays out a self-play match, returning
    - the final position
    - the n x 362 tensor of floats representing the mcts search probabilities
    - the n-ary tensor of floats representing the original value-net estimate
    where n is the number of moves in the game'''
    player = MCTSPlayer(network,
                        resign_threshold=resign_threshold,
                        verbosity=verbosity,
                        num_parallel=SIMULTANEOUS_LEAVES)
    global_n = 0

    # Disable resign in 5% of games
    if random.random() < 0.05:
        player.resign_threshold = -0.999999

    player.initialize_game()

    # Must run this once at the start, so that noise injection actually
    # affects the first move of the game.
    first_node = player.root.select_leaf()
    prob, val = network.run(first_node.position)
    first_node.incorporate_results(prob, val, first_node)

    while True:
        start = time.time()
        player.root.inject_noise()
        current_readouts = player.root.N
        # we want to do "X additional readouts", rather than "up to X readouts".
        while player.root.N < current_readouts + readouts:
            player.tree_search()

        if (verbosity >= 3):
            print(player.root.position)
            print(player.root.describe())

        # Sets is_done to be True if player.should resign.
        if player.should_resign(): # TODO: make this less side-effecty.
            break
        move = player.pick_move()
        player.play_move(move)
        if player.is_done():
            # TODO: actually handle the result instead of ferrying it around as a property.
            player.result = player.position.result()

        if (verbosity >= 2) or (verbosity >= 1 and player.root.position.n % 10 == 9):
            print("Q: {:.5f}".format(player.root.Q))
            dur = time.time() - start
            print("%d: %d readouts, %.3f s/100. (%.2f sec)" % (
                player.root.position.n, readouts, dur / readouts * 100.0, dur), flush=True)
        if verbosity >= 3:
            print("Played >>",
                  coords.to_human_coord(coords.unflatten_coords(player.root.fmove)))


        # TODO: break when i >= 2 * go.N * go.N (where is this being done now??...)

    return player
