import socket
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Client")


class GameStep:
    def __init__(self, client, attrs):
        for key, val in attrs.items():
            setattr(self, key, val)
        self.client = client
        self.ruined = False

    def __str__(self):
        fmt = ('<GameState game={turns=%d, score=%d} '
               'turn={hands=%d score=%d} '
               'dices=%s>')
        args = (self.played_turns, self.total_score,
                self.played_hands, self.turn_score,
                repr(self.dices))
        return fmt % args

    def ruin(self):
        self.ruined = True

    def _send(self, msg):
        if self.ruined:
            raise Exception("This game state has almready been used")
        self.client._send(msg)
        self.ruin()

    def play(self, indices):
        self._send("PLAY %s\n" % json.dumps(indices))

    def trash(self):
        self._send("TRASH\n")

    def bank(self):
        self._send("BANK\n")


class Client:
    class Error(Exception):
        pass

    def __init__(self, name, host="localhost", port=8998):
        self.name = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.lines = []
        logger.info("Connected to %s:%d, waiting for game..." % (host, port))

    def _read_lines(self):
        if not self.lines:
            buf = self.sock.recv(2048).decode()
            if buf == "":
                raise Exception("Disconnected")
            logger.debug("Receiving %s" % repr(buf))
            self.lines += buf.split('\n')
        while self.lines:
            l, self.lines = self.lines[0], self.lines[1:]
            yield l

    def _send(self, msg):
        logger.debug("Sending %s" % repr(msg))
        self.sock.send(msg.encode())

    def __iter__(self):
        # Waiting for STARTING:
        running = False
        while not running:
            for line in self._read_lines():
                if line.startswith('STARTING'):
                    running = True
                    players = json.loads(line.strip().replace('STARTING ', ''))
                    logger.info("Starting ! Players, in this order: %s" % repr(players))
                    break

        name_sent = False
        state = None
        while running:
            for line in self._read_lines():
                if line.startswith('KICK'):
                    running = False
                    break
                if line.startswith('ERROR: '):
                    logger.error(line.strip().replace('ERROR: ', ''))
                if line.startswith('TRASH'):
                    logger.warning("Auto-TRASH after 3 illegal actions")
                if line.startswith('STATE: '):
                    state = json.loads(line.strip().replace('STATE: ', ''))
                if line.startswith('WINNER: '):
                    winner = line.strip().replace('WINNER: ', '')
                    logger.info("The winner is %s", winner)
                if line.startswith('>> '):
                    if not name_sent:
                        self._send("NAME %s" % self.name)
                        name_sent = True
                    else:
                        step = GameStep(self, state)
                        yield step
                        step.ruin()

        logger.info("Kicked")

if __name__ == "__main__":
    # Connect to the game server with your name
    client = Client(name="Titou", host='172.23.218.19', port=8998)

    # Play a game
    for state in client:
        # View the game state
        print(state)

        # Then play one of the following:
        # -------------------------------

        # Play some dices
        state.play([0, 1, 2, 3, 4])

        # OR Save current hand score
        state.bank()

        # OR Abort your turn
        state.trash()
