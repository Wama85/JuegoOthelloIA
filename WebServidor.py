# ==============================================================
# 🔄 VERSIÓN ADAPTADA A WEBSOCKET PARA RENDER
# Solo se cambiaron las partes de conexión TCP -> WebSocket
# ==============================================================
import asyncio            # 🆕 agregado
import websockets          # 🆕 agregado
import json
import numpy as np
import os                  # 🆕 agregado (para puerto dinámico en Render)


class OthelloGame:
    def __init__(self):
        self.board = np.zeros((8, 8), dtype=int)
        self.current_player = 1  # 1 = Negro, 2 = Blanco
        self.game_over = False
        self.winner = None

        # Configuración inicial del tablero
        self.board[3][3] = 2
        self.board[4][4] = 2
        self.board[3][4] = 1
        self.board[4][3] = 1

    def get_valid_moves(self, player):
        valid_moves = []
        for row in range(8):
            for col in range(8):
                if self.is_valid_move(row, col, player):
                    valid_moves.append([row, col])
        return valid_moves

    def is_valid_move(self, row, col, player):
        if self.board[row][col] != 0:
            return False
        opponent = 3 - player
        directions = [(-1, -1), (-1, 0), (-1, 1),
                      (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        for dr, dc in directions:
            r, c = row + dr, col + dc
            found = False
            while 0 <= r < 8 and 0 <= c < 8:
                if self.board[r][c] == opponent:
                    found = True
                    r += dr
                    c += dc
                elif self.board[r][c] == player and found:
                    return True
                else:
                    break
        return False

    def make_move(self, row, col, player):
        if not self.is_valid_move(row, col, player):
            return False
        self.board[row][col] = player
        opponent = 3 - player
        directions = [(-1, -1), (-1, 0), (-1, 1),
                      (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        for dr, dc in directions:
            r, c = row + dr, col + dc
            flips = []
            while 0 <= r < 8 and 0 <= c < 8:
                if self.board[r][c] == opponent:
                    flips.append((r, c))
                    r += dr
                    c += dc
                elif self.board[r][c] == player:
                    for fr, fc in flips:
                        self.board[fr][fc] = player
                    break
                else:
                    break
        return True

    def get_scores(self):
        return {
            "black": int(np.sum(self.board == 1)),
            "white": int(np.sum(self.board == 2))
        }

    def check_game_over(self):
        if not self.get_valid_moves(1) and not self.get_valid_moves(2):
            self.game_over = True
            scores = self.get_scores()
            if scores["black"] > scores["white"]:
                self.winner = 1
            elif scores["white"] > scores["black"]:
                self.winner = 2
            else:
                self.winner = 0
            return True
        return False

    def get_state(self):
        return {
            "board": self.board.tolist(),
            "current_player": int(self.current_player),
            "valid_moves": self.get_valid_moves(self.current_player),
            "scores": self.get_scores(),
            "game_over": self.game_over,
            "winner": self.winner
        }


class GameServer:
    def __init__(self):
        self.clients = []
        self.player_colors = {}
        self.game = None

    async def handler(self, websocket):  # 🔄 cambiado (era handle_client con socket)
        if len(self.clients) >= 2:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Servidor lleno"
            }))
            await websocket.close()
            return

        self.clients.append(websocket)
        color = len(self.clients)
        self.player_colors[websocket] = color

        await websocket.send(json.dumps({
            "type": "welcome",
            "player_color": color,
            "message": f"Eres el jugador {'Negro' if color == 1 else 'Blanco'}"
        }))

        if len(self.clients) == 1:
            await websocket.send(json.dumps({
                "type": "waiting",
                "message": "Esperando segundo jugador..."
            }))
        elif len(self.clients) == 2:
            self.game = OthelloGame()
            msg = {
                "type": "game_start",
                "message": "¡Juego iniciado!",
                "game_state": self.game.get_state()
            }
            # 🆕 envío simultáneo a ambos
            await asyncio.gather(*[c.send(json.dumps(msg)) for c in self.clients])

        try:
            async for data in websocket:  # 🔄 cambiado (antes .recv en loop)
                message = json.loads(data)
                await self.process_message(websocket, message)
        except websockets.ConnectionClosed:
            await self.disconnect(websocket)

    async def process_message(self, websocket, message):  # 🔄 cambiado (async)
        if message.get("type") == "move":
            await self.handle_move(websocket, message)

    async def handle_move(self, websocket, message):  # 🔄 cambiado (async)
        if not self.game or self.game.game_over:
            await websocket.send(json.dumps({
                "type": "move_response",
                "success": False,
                "message": "Juego no activo"
            }))
            return

        color = self.player_colors[websocket]
        if color != self.game.current_player:
            await websocket.send(json.dumps({
                "type": "move_response",
                "success": False,
                "message": "No es tu turno"
            }))
            return

        r, c = message.get("row"), message.get("col")

        if self.game.make_move(r, c, color):
            self.game.current_player = 3 - self.game.current_player
            self.game.check_game_over()
            update = {"type": "game_update", "game_state": self.game.get_state()}
            await asyncio.gather(*[c.send(json.dumps(update)) for c in self.clients])  # 🔄 cambiado
        else:
            await websocket.send(json.dumps({
                "type": "move_response",
                "success": False,
                "message": "Movimiento inválido"
            }))

    async def disconnect(self, websocket):  # 🔄 cambiado (async)
        if websocket in self.clients:
            self.clients.remove(websocket)
            for c in self.clients:
                await c.send(json.dumps({
                    "type": "opponent_disconnected",
                    "message": "Tu oponente se desconectó"
                }))
            self.game = None
            self.player_colors = {}


async def main():  # 🆕 agregado
    port = int(os.environ.get("PORT", 5555))
    async with websockets.serve(GameServer().handler, "0.0.0.0", port):
        print(f"🎮 Servidor WebSocket corriendo en puerto {port}")
        await asyncio.Future()  # Mantiene el servidor vivo


if __name__ == "__main__":  # 🔄 cambiado (usa asyncio)
    asyncio.run(main())
