# Redis
scoresdb: /usr/sbin/redis-server scoresdb.conf

# Game servers
training: python -u server.py training.json
battle: python -u server.py battle.json
tournament: python -u server.py tournament.json
noobs: python -u server.py noobs.json

# Scoreboard websocket servers
scoreboard_battle: python -u scoreboard.py training.json battle.json noobs.json tournament.json
