from random import randint


_5000 = [5] * 5
small_suite = list(range(1, 6))
large_suite = list(range(2, 7))


class InvalidSelection(Exception):
    pass


def get_score(dices, keep_indices):
    """
    Given the dices distributions and the indices of the dices to be kept,
    return the number of remaining dices and the score of kept dices.
    Raise an InvalidSelection in case of error
    """
    if len(keep_indices) == 0:
        raise InvalidSelection("Need to keep at least one dice")

    kept = sorted(dices[i] for i in set(keep_indices))

    # 5000 !
    if kept == _5000:
        return 0, 5000

    # Suites
    if kept == large_suite or kept == small_suite:
        return 0, 1500

    score = 0
    usable = [True for _ in kept]

    # Brelans
    for v in range(1, 7):
        for i in range(len(kept) - 2):
            if kept[i:i+3] == [v, v, v] and all(usable[i:i+3]):
                score += 100*v
                usable[i:i+3] = [False, False, False]

    # 1 and fives
    for i, v in enumerate(kept):
        if not usable[i]:
            continue

        if v == 1:
            score += 100
        elif v == 5:
            score += 50
        else:
            raise InvalidSelection("Cannot use `{}` alone".format(v))

    remaining_dices = len(dices) - len(kept)
    return remaining_dices, score


def get_random_dices(num, faces=6):
    """Return a list of `num` random dice values"""
    return [randint(1, faces) for i in range(num)]


class PlayerState:
    """State for a single player"""
    def __init__(self, get_dices=get_random_dices):
        # Total score
        self.total_score = 0
        # Score of the current turn
        self.turn_score = 0
        # Number of played turns
        self.played_turns = 0
        # Number of played hands in the current turn
        self.played_hands = 0
        # Method for getting new dices (allows pure tests)
        self.get_dices = get_dices
        self.dices = self.get_dices(5)

    def finish_turn(self, accumulate_score=True):
        """Terminate the current turn and initialize a new one"""
        if accumulate_score:
            self.total_score += self.turn_score
        self.played_turns += 1
        self.played_hands = 0
        self.turn_score = 0
        self.dices = self.get_dices(5)

    def play(self, keep_indices):
        """Play a single hand. Return True if the turn can continue"""
        remaining_dices, score = get_score(self.dices, keep_indices)
        self.turn_score += score

        # All dices have been played
        if remaining_dices == 0:
            # All hands have been played
            if self.played_hands == 3:
                return False
            self.played_hands += 1
            remaining_dices = 5
        self.dices = self.get_dices(remaining_dices)
        return True

    def win(self, goal=5000):
        """Return True if the player wins, according to the `goal` score"""
        return self.total_score >= goal

    def dict(self):
        """Return an informational dict of self"""
        serialize = [
            'total_score', 'turn_score',
            'played_hands', 'played_turns',
            'dices'
        ]
        return {name: getattr(self, name) for name in serialize}
