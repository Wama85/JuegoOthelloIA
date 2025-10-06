import asyncio
import websockets
import json
import numpy as np
import os


class OthelloGame:
    def __init__(self):
        self.board = np.zeros((8, 8), dtype=int)
        self.current_player = 1
        self.game_over = False
        self.winner = None
        # Posición inicial
        self.board[3][3] = 2
        self.board[4][4] = 2
        self.board[3][4] = 1
        self.board[4][3] = 1

    def get_valid_moves(self, player):
        valid_moves = []
        for r in range(8):
            for c in range(8):
                if self.is_valid_move(r, c, player):
                    valid_moves.append([r, c])
        return valid_moves

    def is_valid_move(self, row, col, player):
        if self.board[row][col] != 0:
            return False
        opp = 3 - player
        dirs = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
        for dr, dc in dirs:
            r, c = row+dr, col+dc
            found = False
            while 0 <= r < 8 and 0 <= c < 8:
                if self.board[r][c] == opp:
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
        opp = 3 - player
        dirs = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
        for dr, dc in dirs:
            r, c = row+dr, col+dc
            flips = []
            while 0 <= r < 8 and 0 <= c < 8:
                if self.board[r][c] == opp:
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
        black = int(np.sum(self.board == 1))
        white = int(np.sum(self.board == 2))
        return {"black": black, "white": white}

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

    async def handler(self, websocket):
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
            await asyncio.gather(*[c.send(json.dumps(msg)) for c in self.clients])

        try:
            async for data in websocket:
                message = json.loads(data)
                await self.process_message(websocket, message)
        except websockets.ConnectionClosed:
            await self.disconnect(websocket)

    # ==========================================================
    # 🔧 Mensajes procesados (join + move)
    # ==========================================================
    async def process_message(self, websocket, message):
        try:
            tipo = message.get("type")

            if tipo == "join":
                nombre = message.get("name", "IA")
                await websocket.send(json.dumps({
                    "type": "ack",
                    "message": f"Jugador {nombre} conectado correctamente"
                }))
                return

            if tipo == "move":
                await self.handle_move(websocket, message)
                return

            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Tipo de mensaje desconocido: {tipo}"
            }))
        except Exception as e:
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Error interno del servidor: {str(e)}"
            }))
            import traceback
            traceback.print_exc()

    # ==========================================================
    # 🔥 Lógica de movimientos
    # ==========================================================
    async def handle_move(self, websocket, message):
        if not self.game or self.game.game_over:
            await websocket.send(json.dumps({
                "type": "move_response",
                "success": False,
                "message": "Juego no activo"
            }))
            return

        color = self.player_colors.get(websocket)
        if color != self.game.current_player:
            await websocket.send(json.dumps({
                "type": "move_response",
                "success": False,
                "message": "No es tu turno"
            }))
            return

        r, c = message.get("row"), message.get("col")
        if r is None or c is None:
            await websocket.send(json.dumps({
                "type": "move_response",
                "success": False,
                "message": "Movimiento inválido (faltan coordenadas)"
            }))
            return

        if self.game.make_move(r, c, color):
            print(f"🎯 Jugador {color} movió a ({r},{c})")  # 🆕 Log en consola
            self.game.current_player = 3 - self.game.current_player
            self.game.check_game_over()
            update = {
                "type": "game_update",
                "game_state": self.game.get_state()
            }
            await asyncio.gather(*[c.send(json.dumps(update)) for c in self.clients])
        else:
            await websocket.send(json.dumps({
                "type": "move_response",
                "success": False,
                "message": "Movimiento inválido"
            }))

    # ==========================================================
    # 🔻 Desconexión
    # ==========================================================
    async def disconnect(self, websocket):
        if websocket in self.clients:
            self.clients.remove(websocket)
            for c in self.clients:
                await c.send(json.dumps({
                    "type": "opponent_disconnected",
                    "message": "Tu oponente se desconectó"
                }))
            self.game = None
            self.player_colors = {}


# ==============================================================
# MAIN
# ==============================================================
async def main():
    port = int(os.environ.get("PORT", 5555))
    async with websockets.serve(GameServer().handler, "0.0.0.0", port):
        print(f"🚀 Servidor WebSocket corriendo en puerto {port}")
        await asyncio.Future()  # Mantenerlo activo


if __name__ == "__main__":
    asyncio.run(main())
