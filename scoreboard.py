import asyncio
from aiohttp import web
import asyncio_redis as aioredis
import websockets
import json


def scoreboard_websocket(title, redis_scoreboard, address, ws_port, **kwargs):
    loop = asyncio.get_event_loop()
    scores = {}
    clients = []

    def get_redis():
        return aioredis.Connection.create('scoresdb.sock', 0,
                                          db=redis_scoreboard)

    def update_score(r, name):
        value = yield from r.hgetall(name)
        entry = {}
        for item in value:
            key, val = yield from item
            entry[key] = int(val)
        scores[name] = entry

    def setup_redis():
        r = yield from get_redis()

        keys = yield from r.keys('*')
        for key_future in keys:
            key = yield from key_future
            yield from update_score(r, key)

        p = yield from r.start_subscribe()
        yield from p.subscribe(['__keyevent@%d__:hincrby' % redis_scoreboard])
        return r, p

    r, p = loop.run_until_complete(setup_redis())
    print("Connected to Redis")

    def format_response():
        scores_list = [
            {'name': n, 'count': s.get('count', 0), 'won': s.get('won', 0)}
            for n, s in scores.items()
        ]
        r = json.dumps({
            'title': title,
            'scores': scores_list,
        })
        return r

    def accept_client(ws, path):
        clients.append(ws)
        yield from ws.send(format_response())
        while ws.open:
            yield from asyncio.sleep(1)

    def new_score(key):
        r = yield from get_redis()
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

    start_server = websockets.serve(accept_client, address, ws_port)
    loop.run_until_complete(start_server)
    print("Scores for", title,
          "published on", "ws://%s:%d" % (address, ws_port))
    asyncio.async(pump_events())


webapp = web.Application()
webapp.GET = lambda route: lambda func: webapp.router.add_get(route, func)


@webapp.GET('/')
def index(req):
    content = open('scoreboard/index.html').read()
    return web.Response(text=content, content_type='text/html')

if __name__ == "__main__":
    from sys import argv

    boards = []

    for arg in argv[1:]:
        config = json.load(open(arg))
        boards.append(config)
        if 'ws_port' in config:
            scoreboard_websocket(**config)

    @webapp.GET('/boards.json')
    def list_boards(req):
        return web.json_response(boards)

    web.run_app(webapp, host='localhost', port=8000)
