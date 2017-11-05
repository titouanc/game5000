import Task
import Html exposing (..)
import Html.Attributes exposing (..)
import Html.Events exposing (..)
import Json.Decode exposing (Decoder, decodeString, list, int, string, field, map2, map3)
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


-- The app model
type alias PlayerSort = Player -> Int
type alias Model = { board: Board, sortColumn: PlayerSort }
type Msg = NewScores String
         | SortBy PlayerSort

init : (Model, Cmd Msg)
init = ({sortColumn=ratio, board=emptyBoard}, Cmd.none)

update : Msg -> Model -> (Model, Cmd Msg)
update msg model =
  case msg of
    NewScores str ->
      case decodeString decodeBoard str of
        Err _ -> (model, Cmd.none)
        Ok newboard -> ({model | board=newboard}, Cmd.none)
    SortBy col -> ({model | sortColumn=col}, Cmd.none)


-- SUBSCRIPTIONS
subscriptions : Model -> Sub Msg
subscriptions model =
  WebSocket.listen "ws://localhost:8888/" NewScores


unMaybe : List (Maybe a) -> Maybe (List a)
unMaybe l =
    case l of
        [] -> Just []
        head::tail -> let rtail = unMaybe tail
                      in case (head, rtail) of
                          (Just h, Just t) -> Just <| h::t
                          _ -> Nothing


-- VIEW
columns : List (String, PlayerSort)
columns = [ ("Games played", .count), ("Games won", .won), ("Score", ratio) ]

-- Single <td> element, annotated if it's the best
cellRenderer : Player -> (String, PlayerSort) -> Int -> Html Msg
cellRenderer player (name, getter) best =
    let val = getter player
        txt = toString val |> text
        content = if val == best then span [] [ txt ] else txt
    in td [] [ content ]

-- <tr> for a player
playerRow : List Int -> Player -> Html Msg
playerRow bestScores player = 
    let cells = List.map2 (cellRenderer player) columns bestScores
    in tr [] <| (th [] [ text player.name ])::cells

-- Single <th> element
headerCellRenderer : (String, PlayerSort) -> Html Msg
headerCellRenderer (name, func) = th [ onClick <| SortBy func ] [text name]

-- Table with headers and content
tableBoard : PlayerSort -> List Player -> Html Msg
tableBoard sortColumn data =
    let sortableHeaders = List.map headerCellRenderer columns
        titleRow = tr [] <| (th [] [ text "Player" ])::sortableHeaders
        sorted = List.sortBy (\x -> 0 - sortColumn x) data
        bestInCategory (name, func) = List.maximum <| List.map func sorted
        bests = List.map bestInCategory columns
        contents = case unMaybe bests of
            Just theBests -> List.map (playerRow theBests) sorted
            Nothing -> []
    in table [] <| titleRow::contents


view : Model -> Html Msg
view model = div [] [ h1 [] [ text model.board.title ]
                    , tableBoard model.sortColumn model.board.scores
                    ]

-- Main
main = Html.program { init = init
                    , view = view
                    , update = update
                    , subscriptions = subscriptions
                    }
