from game import get_score, PlayerState


def get_range_dices(num):
    return range(1, num+1)


def test_player_state():
    ps = PlayerState(get_range_dices)
    ps.play(range(5))
    assert ps.current_turn == 1500
    assert ps.played_hands == 1
    assert ps.played_turns == 0

    ps.finish_turn()
    assert ps.current_turn == 0
    assert ps.played_hands == 0
    assert ps.played_turns == 1
    assert ps.score == 1500


def test_get_score():
    assert get_score([5, 5, 5, 5, 5], range(5)) == (0, 5000)
    assert get_score(range(2, 7), range(5)) == (0, 1500)
    assert get_score([2, 6, 3, 3, 3], range(2, 5)) == (2, 300)
    assert get_score([5, 1, 3, 3, 3], range(5)) == (0, 450)
    assert get_score([5, 6, 3, 3, 3], [0, 2, 3, 4]) == (1, 350)

    assert get_score([1], [0]) == (0, 100)
    assert get_score([1, 3, 3, 3], range(4)) == (0, 400)
