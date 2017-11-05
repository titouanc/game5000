import Debug exposing (log)
import Html exposing (..)
import Html.Attributes exposing (..)
import Html.Events exposing (..)
import Json.Decode exposing (Decoder, decodeString, list, int, string, field, map2, map3, map4)
import Http
import WebSocket

-- A player entry in the board
type alias Player = { name: String, count: Int, won: Int }

decodePlayer = map3 Player
                    (field "name" string)
                    (field "count" int)
                    (field "won" int)

ratio : Player -> Int
ratio player = round <| 100 * toFloat player.won / toFloat player.count


-- The board itself
type alias Board = { title: String, scores: List Player}

decodeBoard = map2 Board
                   (field "title" string)
                   (field "scores" <| Json.Decode.list decodePlayer)

emptyBoard : Board
emptyBoard = {title="Scoreboard", scores=[]}


-- A board information listed in /boards.json
type alias BoardInfo = {ws_port: Int, game_port: Int, address: String, title: String}

decodeBoardInfo = map4 BoardInfo
                       (field "ws_port" int)
                       (field "port" int)
                       (field "address" string)
                       (field "title" string)
                |> Json.Decode.list

wsurl : BoardInfo -> String
wsurl {address, ws_port} = "ws://" ++ address ++ ":" ++ toString ws_port ++ "/"

ncCommand : BoardInfo -> String
ncCommand {address, game_port} = "nc " ++ address ++ " " ++ toString game_port


-- The app model

type alias PlayerSort = (String, Player -> Int)

type alias Model = { board: Board
                   , infos: Maybe BoardInfo
                   , sortKey: PlayerSort
                   , list_boards: List BoardInfo}


type Msg = NewScores String
         | SortBy PlayerSort
         | ListBoards (Result Http.Error (List BoardInfo))
         | Watch BoardInfo


getBoards : Cmd Msg
getBoards = Http.get "/boards.json" decodeBoardInfo |> Http.send ListBoards

freshModel : Model
freshModel = {sortKey=("Score", ratio)
             , board=emptyBoard
             , infos=Nothing
             , list_boards=[]}

init : (Model, Cmd Msg)
init = (freshModel, getBoards)

update : Msg -> Model -> (Model, Cmd Msg)
update msg model =
  let newmodel = case msg of
      SortBy col -> {model | sortKey=col}
      Watch board -> {model | infos=Just board}
      ListBoards (Err _) -> model
      ListBoards (Ok s) ->
          let newmodel = {model | list_boards=s} -- Update list of known boards
          in case s of [] -> newmodel                       -- No boards at all
                       board::_ -> {newmodel | infos=Just board} -- Show first board
      NewScores str -> case decodeString decodeBoard str of
          Err _ -> model
          Ok newboard -> {model | board=newboard}
  in (newmodel, Cmd.none)


-- SUBSCRIPTIONS
subscriptions : Model -> Sub Msg
subscriptions model =
    case model.infos of
        Nothing -> Sub.batch []
        Just board -> WebSocket.listen (wsurl board) NewScores


unMaybe : List (Maybe a) -> Maybe (List a)
unMaybe l =
    case l of
        [] -> Just []
        head::tail -> let rtail = unMaybe tail
                      in case (head, rtail) of
                          (Just h, Just t) -> Just <| h::t
                          _ -> Nothing


-- VIEW
columns : List PlayerSort
columns = [ ("Games played", .count), ("Games won", .won), ("Score", ratio) ]

goldStyle = style [("color", "gold"), ("font-size", "125%")]

-- Single <td> element, annotated if it's the best
cellRenderer : Player -> PlayerSort -> Int -> Html Msg
cellRenderer player (name, getter) best =
    let val = getter player
        txt = toString val |> text
        content = if val == best
                  then [ span [ goldStyle ] [ text "★" ]
                       , txt 
                       ]
                  else [ txt ]
    in td [ style [("text-align", "right")] ] content

-- <tr> for a player
playerRow : List Int -> Player -> Html Msg
playerRow bestScores player = 
    let cells = List.map2 (cellRenderer player) columns bestScores
    in tr [] <| (th [] [ text player.name ])::cells

-- Single <th> element
headerCellRenderer : String -> PlayerSort -> Html Msg
headerCellRenderer sortColumn (name, func) =
    let content = if sortColumn == name
                  then [text "★", text name]
                  else [text name]
    in th [ style [("text-align", "right")] ]
          [a [ href "#", onClick <| SortBy (name, func), style [("color", "black")] ]
             content ]

-- Table with headers and content
tableBoard : PlayerSort -> List Player -> Html Msg
tableBoard (sortColumn, sortFunc) data =
    let sortableHeaders = List.map (headerCellRenderer sortColumn) columns
        titleRow = tr [] <| (th [] [ text "Player" ])::sortableHeaders
        sorted = List.sortBy (\x -> 0 - sortFunc x) data
        bestInCategory (name, func) = List.maximum <| List.map func sorted
        bests = List.map bestInCategory columns
        contents = case unMaybe bests of
            Just theBests -> List.map (playerRow theBests) sorted
            Nothing -> []
    in table [ style [("width", "98%")] ] <| titleRow::contents


view : Model -> Html Msg
view model =
    let linkStyle = style [("margin-left", "1em"), ("color", "black")]
        globalStyle = style [ ("font-size", "150%"), ("width", "100%")]
        codeStyle = style [("background-color", "black"), ("color", "white"), ("padding", ".2em")]
        link board = a [ linkStyle, href "#", onClick <| Watch board]
                       [ text board.title ]
        boards = List.map link model.list_boards
        linkbar = small [style [("font-size", "50%")]] boards
        table = tableBoard model.sortKey model.board.scores
        body = case model.infos of
            Nothing -> [ h1 [] [text "Loading..."] ]
            Just x -> [ h1 [] [text x.title, linkbar]
                      , div [] [ text "Try this server:"
                               , code [codeStyle] [ ncCommand x |> text ]]
                      , table]
    in div [globalStyle] body

-- Main
main = Html.program { init = init
                    , view = view
                    , update = update
                    , subscriptions = subscriptions
                    }
