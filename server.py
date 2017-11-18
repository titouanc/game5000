import socket
import json
import logging
from threading import Thread
from random import shuffle
from redis import Redis

from game import PlayerState

# logging.setLoggerClass(ColoredLogger)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("Server")


class ScoresDB(Redis):
    def __init__(self, db):
        logger.debug("Connect to redis db=%d" % db)
        super(ScoresDB, self).__init__(unix_socket_path='scoresdb.sock', db=db)

    def alter(self, key, by, names):
        for name in names:
            logger.info("%s.%s += %d" % (name, key, by))
            self.hincrby(name, key, by)
        return self

    def inc_played(self, names):
        return self.alter("count", 1, names)

    def inc_score(self, names):
        return self.alter("won", 1, names)

    def dec_score(self, names):
        return self.alter("won", -1, names)


class InvalidCommand(Exception):
    pass


class Client:
    def __init__(self, fd):
        self.fd, self.state = fd, PlayerState()
        self.name = '%s:%d' % self.fd.getpeername()

    def send(self, text):
        self.fd.send(text.encode())

    def recv(self):
        return self.fd.recv(1024).decode()

    def send_state(self):
        serialized = json.dumps(self.state.dict(), sort_keys=True)
        self.send('STATE: ' + serialized + '\n')

    def run_command(self, line):
        line_upper = line.upper()
        if line_upper.startswith('TRASH'):
            self.state.finish_turn(False)
            return False
        if line_upper.startswith('BANK'):
            if len(self.state.dices) != 5:
                raise InvalidCommand("Cannot bank with all dices played")
            self.state.finish_turn()
            return False
        if line_upper.startswith('NAME '):
            if self.state.played_turns > 0:
                raise InvalidCommand("Cannot change name after first turn")
            name = line[5:].split('\n')[0].strip()
            if len(name) == 0:
                raise InvalidCommand("Name cannot be empty")
            self.name = name
            return True
        if line_upper.startswith('PLAY '):
            to_keep = json.loads(line[5:].strip())
            if len(to_keep) == 0:
                raise InvalidCommand("Need at least one dice to keep")
            return self.state.play(to_keep)
        raise InvalidCommand()

    def run_turn(self):
        can_play = True

        while can_play:
            successful_cmd = False

            for retries in range(3):
                self.send_state()
                self.send(">> ")

                # Client did not respond in time: KICK
                try:
                    line = self.recv()
                except socket.timeout:
                    logger.warning("Client %s timeout" % self.name)
                    return False

                logger.debug("Received %s" % repr(line))

                # Client disconnected
                if not line:
                    return False

                try:
                    can_play = self.run_command(line)
                    successful_cmd = True
                    break
                except Exception as err:
                    msg = "ERROR: %s %s\n" % (err.__class__.__name__, str(err))
                    self.send(msg)
                    fmt = "Error in client trial %d/3 from %s (%s)"
                    logger.info(fmt % (1 + retries, self.name, msg))
            if not successful_cmd:
                can_play = self.run_command('TRASH')
                logger.warning("3 consecutive errors. TRASH")
                self.send("TRASH\n")

        # All dices consumed in the last turn, BANK it
        if not self.state.dices:
            self.run_command('BANK')
        return True


def run_table(fds, redis_scoreboard):
    fds = list(fds)
    shuffle(fds)
    table_clients = [Client(fd) for fd in fds]

    names = [client.name for client in table_clients]
    for client in table_clients:
        client.send("STARTING %s\n" % json.dumps(names))

    logger.info("Starting new table with %s" % repr(names))

    def disconnect(client):
        try:
            client.send("KICK\n")
        except:
            pass
        logger.info("Closed connection with %s" % client.name)
        client.fd.close()

    def disconnect_all():
        for client in table_clients:
            disconnect(client)

    def tell_winner(name):
        for client in table_clients:
            client.send("WINNER: %s\n" % name)

    running = True
    while running:
        for client in table_clients:
            connected = client.run_turn()
            if not connected and redis_scoreboard is not None:
                redis = ScoresDB(redis_scoreboard)
                redis.dec_score([client.name]).inc_played([client.name])
                running = False
                break
            elif client.state.win():
                tell_winner(client.name)
                if redis_scoreboard is not None:
                    redis = ScoresDB(redis_scoreboard)
                    redis.inc_score([client.name])
                    redis.inc_played(c.name for c in table_clients)
                running = False
                break
    disconnect_all()


def run_server(address='127.0.0.1', port=8998,
               n_players=1, timeout=None, redis_scoreboard=None,
               multithreaded=False, **kwargs):
    bind_ip = address
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.bind((bind_ip, port))
    if multithreaded:
        sock.listen(512)
    else:
        sock.listen(1)

    logger.info("Server started")

    clients = set()
    while True:
        while len(clients) < n_players:
            fd, (ip, port) = sock.accept()
            fd.settimeout(timeout)
            clients.add(fd)
            logger.info("Connection from %s:%d" % (ip, port))

        started = False
        if multithreaded:
            try:
                Thread(target=run_table, args=(clients, redis_scoreboard)).start()
                started = True
            except:
                pass
        if not started:
            try:
                run_table(clients, redis_scoreboard)
            except:
                pass
        clients = set()


if __name__ == "__main__":
    from sys import argv

    config = {}
    if len(argv) > 1:
        config = json.load(open(argv[1]))

    run_server(**config)
