from fastapi import APIRouter, HTTPException, Request

from controllers.game_controller import GameLogic
from models.schema import Code, GameResultRequest


class GameRoutes:
    def __init__(self):
        self.router = APIRouter(prefix="/game", tags=["game"])
        self.register_routes()

    def get_game_logic(self, request: Request) -> GameLogic:
        username = request.session.get("username")

        if not username:
            raise HTTPException(status_code=401, detail="You need to login first")

        return GameLogic(username)

    def get_username(self, request: Request) -> str:
        username = request.session.get("username")

        if not username:
            raise HTTPException(status_code=401, detail="You need to login first")

        return username

    def register_routes(self):
        @self.router.post("/start-solo")
        def start_game(request: Request):
            game = self.get_game_logic(request)
            return game.start_game_controller()

        @self.router.post("/submit")
        def submit_code(payload: Code, request: Request):
            username = self.get_username(request)
            return GameLogic.submit_code_controller(payload, username)

        @self.router.post("/result")
        def result_code(payload: GameResultRequest, request: Request):
            username = self.get_username(request)
            return GameLogic.get_result_controller(payload.game_id, username)


game_routes = GameRoutes()
router = game_routes.router
