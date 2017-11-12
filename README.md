# Rules

This game is derived from "5000", a dices game where the goal is to get 5000 points.


## Playing a game
One or more players (depending on the server configuration) sit around a table.
The game starts, and all players play a turn each one after the other. 

The first player to reach 5000 wins the game and gets +1 in the scoreboard,
and all players get their played games counted. If you disconnect from the game
server before the game ends, the game ends, you get penalty of -1 to the
scoreboard, and the played games of the other players don't get incremented,
while yours is incremented.


## Playing a turn

During a turn, each player can play up to 3 hands. During the second hand of a
turn, the points earned during the hand are doubled. During the third hand,
they are tripled.

At the start of the first hand, you roll 5 dices. From now, you can do 3 things:

1. **PLAY** a valid combination of dices, which augments your turn score
2. You can **TRASH** your roll, losing all the point from your current turn.
3. You can **BANK** your turn score into your total score.
   You can do this only if you did not play any of the dices in this hand

If there are remaining dices, they are rerolled, and you can play action 1 or 2
again. When all dices are played, a new hand is started. You can play up to 3
successive hands, the last one is automatically BANKed.

## Valid dices combinations

* **"5000"** `5,5,5,5,5`: 5000 points
* **Suites** `1,2,3,4,5` or `2,3,4,5,6`: 1500 points
* **Brelans**
    * `1,1,1`: 100 points
    * `2,2,2`: 200 points
    * `3,3,3`: 300 points
    * `4,4,4`: 400 points
    * `5,5,5`: 500 points
    * `6,6,6`: 600 points
* **Alone**
    * `1`: 100 points
    * `5`:  50 points


# The game server

All the game servers scores are presented on the scoreboard. You can also find
how to connect to the servers on each of the scoreboard tab.

## Environments

There are 3 different game servers:

* **Training**: You play alone, such that you can only win (+1) or lose (-1) by
  diconnection. You have 1 minute to play.
* **Battle**: You play by 2, such that you can win (+1), don't win (0) or lose
  by disconnection (-1). You have 1 second to play
* **Tournament**: You play by 3, and you have 1 second to play. There can be only
  a single game at a time (no multithreading), and it will be used for final
  scoring. **Please don't use this server until instructed to do so !**

## Playing with netcat

The only game environment where you can play interactively is the **Training**.
Use it to familiarize yourself with the game environment and commands.

You can connect with netcat:

```
$ nc <server> <port>
```

Once all the players are connected, the game starts, and you get the list of
all players around your table. You the receive your state of the game.

* `dices`: The dices you rolled
* `played_hands`: The number of hands you already played in this turn
* `played_turns`: The number of turns you already played in the game
* `total_score`: Your number of points in the game
* `turn_score`: The points you earned in the current turn

You are then instructed to answer with the prompt `>>`

```
STARTING ["127.0.0.1:37930"]
STATE: {"dices": [5, 4, 2, 6, 3], "played_hands": 0, "played_turns": 0, "total_score": 0, "turn_score": 0}
>>
```

You can register your name to appear in the scoreboard. Otherwise, your name
will be your ip and port, which is likely to change between games (you can therefore
not progress in the scoreboard). Changing your name does not count as a turn
(you keep the same state).

**NOTE:** You can only register your name during the first turn.

```
>> NAME titou
STATE: {"dices": [5, 4, 2, 6, 3], "played_hands": 0, "played_turns": 0, "total_score": 0, "turn_score": 0}
>>
```

Then you can play, giving the dices indexes you want to keep, as a list. For
instance, let's play the first '5' (which is index `0`):

```
>> PLAY [0]
STATE: {"dices": [6, 3, 3, 4], "played_hands": 0, "played_turns": 0, "total_score": 0, "turn_score": 50}
>>
```

Yeeehaaaaa ! We got 50 points for this turn !

But now, we cannot play any of the rolled dices. We therefore have to trash them,
and wait for the next turn (notice how `played_turns` was incremented). Because
you trashed your turn score, the total score doesn't get incremented.

```
>> TRASH
STATE: {"dices": [5, 6, 3, 3, 6], "played_hands": 0, "played_turns": 1, "total_score": 0, "turn_score": 0}
```

We then play the next turn:

* Use the first '5'
* In the next roll we have a brelan of 2's
* Then we use the remaining '1'

```
>> PLAY [0]
STATE: {"dices": [2, 2, 2, 4], "played_hands": 0, "played_turns": 1, "total_score": 0, "turn_score": 50}
>> PLAY [0, 1, 2]
STATE: {"dices": [1], "played_hands": 0, "played_turns": 1, "total_score": 0, "turn_score": 250}
>> PLAY [0]
STATE: {"dices": [6, 6, 2, 4, 6], "played_hands": 1, "played_turns": 1, "total_score": 0, "turn_score": 350}
>>
```

Now we have 2 options:

#### Continue to play

You can continue to play, and all the points you will earn from now are doubled.

#### Save your points (BANK)

If you do this, your turn ends, and your `turn_score` is added to your
`total_score`.

```
>> BANK
STATE: {"dices": [2, 3, 1, 6, 4], "played_hands": 0, "played_turns": 2, "total_score": 350, "turn_score": 0}
```

