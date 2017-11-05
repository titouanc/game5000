import asyncio
import asyncio_redis as aioredis
import websockets
import json


@asyncio.coroutine
def get_redis(db):
    return aioredis.Connection.create('scoresdb.sock', 0, db=db)


@asyncio.coroutine
def async_increment_played(names, db):
    r = yield from get_redis(db)
    for name in names:
        yield from r.hincrby(name, "played", 1)
    r.close()


@asyncio.coroutine
def async_increment_score(name, db=0):
    r = yield from get_redis(db)
    yield from r.hincrby(name, "won", 1)
    r.close()


@asyncio.coroutine
def async_decrement_score(name, db=0):
    r = yield from get_redis(db)
    yield from r.hincrby(name, "won", -1)
    r.close()


def synchronous(func):
    loop = asyncio.get_event_loop()

    def inner(*args, **kwargs):
        coroutine = func(*args, **kwargs)
        return loop.run_until_complete(coroutine)
    return inner


increment_played = synchronous(async_increment_played)
increment_score = synchronous(async_increment_score)
decrement_score = synchronous(async_decrement_score)


def scoreboard_websocket(title, db, address, port):
    loop = asyncio.get_event_loop()
    scores = {}
    clients = []

    def update_score(r, name):
        value = yield from r.hgetall(name)
        entry = {}
        for item in value:
            key, val = yield from item
            entry[key] = int(val)
        scores[name] = entry

    def setup_redis():
        r = yield from get_redis(db)

        keys = yield from r.keys('*')
        for key_future in keys:
            key = yield from key_future
            yield from update_score(r, key)

        p = yield from r.start_subscribe()
        yield from p.subscribe(['__keyevent@0__:hincrby'])
        return r, p

    r, p = loop.run_until_complete(setup_redis())
    print("Connected to Redis")

    def format_response():
        scores_list = [
            {'name': n, 'count': s['count'], 'won': s['won']}
            for n, s in scores.items()
        ]
        r = json.dumps({
            'title': title,
            'scores': scores_list,
        })
        print(r)
        return r

    def accept_client(ws, path):
        clients.append(ws)
        print("New client", ws)
        yield from ws.send(format_response())
        while ws.open:
            yield from asyncio.sleep(1)
        print("Client quit", ws)

    def new_score(key):
        r = yield from get_redis(db)
        yield from update_score(r, key)
        payload = format_response()
        active = [True for _ in clients]
        for i, ws in enumerate(clients):
            try:
                yield from ws.send(payload)
            except websockets.exceptions.ConnectionClosed:
                active[i] = False
                ws.close()
        r.close()
        clients[:] = [c for i, c in enumerate(clients) if active[i]]

    def pump_events():
        while True:
            evt = yield from p.next_published()
            asyncio.async(new_score(evt.value))

    start_server = websockets.serve(accept_client, address, port)
    loop.run_until_complete(start_server)
    print("Websocket started. Pumping events...")
    loop.run_until_complete(pump_events())


if __name__ == "__main__":
    from sys import argv
    db = 0
    name = "Game of 5000"

    if len(argv) > 1:
        port = int(argv[1])
    if len(argv) > 2:
        name = argv[2]

    scoreboard_websocket(name, db, 'localhost', 8888)
