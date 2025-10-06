import asyncio
import websockets
import json
import pygame
import numpy as np
import threading
import math
import random


class Lanzador:
    def __init__(self, host="wss://juegoothelloia.onrender.com", nombre="IA_EXPERTA"):
        self.host = host
        self.nombre = nombre
        self.ws = None
        self.juego_activo = False
        self.color_jugador = None
        self.tablero = np.zeros((8, 8), dtype=int)
        self.turno_actual = 1

        # Visual
        self.celda = 75
        self.colores = {0: (0, 128, 0), 1: (0, 0, 0), 2: (255, 255, 255)}

    # ==========================================================
    # Conexión WebSocket
    # ==========================================================
    async def conectar_servidor(self):
        uri = self.host
        print(f"🔌 Conectando a {uri} ...")
        try:
            async with websockets.connect(uri) as websocket:
                self.ws = websocket
                print("✅ Conectado al servidor WebSocket")

                await self.enviar_mensaje({"type": "join", "name": self.nombre})
                async for msg in websocket:
                    data = json.loads(msg)
                    self.procesar_mensaje(data)
        except Exception as e:
            print(f"❌ Error al conectar al servidor: {e}")

    async def enviar_mensaje(self, mensaje):
        try:
            if self.ws:
                await self.ws.send(json.dumps(mensaje))
        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")

    # ==========================================================
    # Procesamiento de mensajes
    # ==========================================================
    def procesar_mensaje(self, data):
        tipo = data.get("type")

        if tipo == "welcome":
            self.color_jugador = data["player_color"]
            print(f"🎮 {data['message']}")
        elif tipo == "waiting":
            print("⌛ Esperando segundo jugador...")
        elif tipo == "game_start":
            self.juego_activo = True
            estado = data["game_state"]
            self.tablero = np.array(estado["board"])
            self.turno_actual = estado["current_player"]
            print("✅ ¡Juego iniciado!")
        elif tipo == "game_update":
            estado = data["game_state"]
            self.tablero = np.array(estado["board"])
            self.turno_actual = estado["current_player"]

            if self.turno_actual == self.color_jugador and not estado["game_over"]:
                threading.Thread(target=self.jugar_turno, daemon=True).start()
        elif tipo == "opponent_disconnected":
            print("⚠️  Oponente desconectado.")
        elif tipo == "move_response":
            print(data["message"])

    # ==========================================================
    # Interfaz Pygame
    # ==========================================================
    def iniciar_interfaz(self):
        pygame.init()
        screen = pygame.display.set_mode((600, 600))
        pygame.display.set_caption(f"Othello - {self.nombre}")

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return

            screen.fill((0, 128, 0))
            for i in range(9):
                pygame.draw.line(screen, (0, 0, 0), (0, i * self.celda), (600, i * self.celda), 2)
                pygame.draw.line(screen, (0, 0, 0), (i * self.celda, 0), (i * self.celda, 600), 2)

            for r in range(8):
                for c in range(8):
                    valor = self.tablero[r][c]
                    if valor != 0:
                        color = self.colores[valor]
                        x = c * self.celda + self.celda // 2
                        y = r * self.celda + self.celda // 2
                        pygame.draw.circle(screen, color, (x, y), 30)

            pygame.display.flip()
            pygame.time.delay(100)

    # ==========================================================
    # Iniciar programa
    # ==========================================================
    def iniciar(self):
        threading.Thread(target=self.iniciar_interfaz, daemon=True).start()
        asyncio.run(self.conectar_servidor())

    # ==========================================================
    # 🔥 Lógica de la IA (Minimax con heurística)
    # ==========================================================
    def jugar_turno(self):
        mejor_mov = self.mejor_movimiento(self.tablero, self.color_jugador, profundidad=3)
        if mejor_mov:
            r, c = mejor_mov
            print(f"🤖 IA ({self.nombre}) juega en ({r}, {c})")
            asyncio.run(self.enviar_mensaje({"type": "move", "row": int(r), "col": int(c)}))

    # ==========================================================
    # Evaluación heurística avanzada
    # ==========================================================
    def evaluar_tablero(self, tablero, jugador):
        oponente = 3 - jugador
        pesos = np.array([
            [120, -20,  20,  5,  5,  20, -20, 120],
            [-20, -40,  -5, -5, -5,  -5, -40, -20],
            [20,  -5,  15,  3,  3,  15,  -5,  20],
            [5,   -5,   3,  3,  3,   3,  -5,   5],
            [5,   -5,   3,  3,  3,   3,  -5,   5],
            [20,  -5,  15,  3,  3,  15,  -5,  20],
            [-20, -40,  -5, -5, -5,  -5, -40, -20],
            [120, -20,  20,  5,  5,  20, -20, 120]
        ])
        return np.sum((tablero == jugador) * pesos) - np.sum((tablero == oponente) * pesos)

    # ==========================================================
    # Funciones auxiliares de juego
    # ==========================================================
    def obtener_movimientos_validos(self, tablero, jugador):
        validos = []
        for r in range(8):
            for c in range(8):
                if self.movimiento_valido(tablero, r, c, jugador):
                    validos.append((r, c))
        return validos

    def movimiento_valido(self, tablero, row, col, jugador):
        if tablero[row][col] != 0:
            return False
        oponente = 3 - jugador
        dirs = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
        for dr, dc in dirs:
            r, c = row+dr, col+dc
            found = False
            while 0 <= r < 8 and 0 <= c < 8:
                if tablero[r][c] == oponente:
                    found = True
                    r += dr
                    c += dc
                elif tablero[r][c] == jugador and found:
                    return True
                else:
                    break
        return False

    def aplicar_movimiento(self, tablero, row, col, jugador):
        nuevo = np.copy(tablero)
        if not self.movimiento_valido(nuevo, row, col, jugador):
            return nuevo
        nuevo[row][col] = jugador
        oponente = 3 - jugador
        dirs = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
        for dr, dc in dirs:
            r, c = row+dr, col+dc
            flips = []
            while 0 <= r < 8 and 0 <= c < 8:
                if nuevo[r][c] == oponente:
                    flips.append((r, c))
                    r += dr
                    c += dc
                elif nuevo[r][c] == jugador:
                    for fr, fc in flips:
                        nuevo[fr][fc] = jugador
                    break
                else:
                    break
        return nuevo

    # ==========================================================
    # 🔁 Minimax con poda alfa-beta
    # ==========================================================
    def minimax(self, tablero, profundidad, jugador, maximizando, alpha, beta):
        movimientos = self.obtener_movimientos_validos(tablero, jugador)
        if profundidad == 0 or not movimientos:
            return self.evaluar_tablero(tablero, self.color_jugador), None

        if maximizando:
            mejor_valor = -math.inf
            mejor_mov = None
            for mov in movimientos:
                nuevo_tablero = self.aplicar_movimiento(tablero, mov[0], mov[1], jugador)
                valor, _ = self.minimax(nuevo_tablero, profundidad - 1, 3 - jugador, False, alpha, beta)
                if valor > mejor_valor:
                    mejor_valor = valor
                    mejor_mov = mov
                alpha = max(alpha, valor)
                if beta <= alpha:
                    break
            return mejor_valor, mejor_mov
        else:
            peor_valor = math.inf
            peor_mov = None
            for mov in movimientos:
                nuevo_tablero = self.aplicar_movimiento(tablero, mov[0], mov[1], jugador)
                valor, _ = self.minimax(nuevo_tablero, profundidad - 1, 3 - jugador, True, alpha, beta)
                if valor < peor_valor:
                    peor_valor = valor
                    peor_mov = mov
                beta = min(beta, valor)
                if beta <= alpha:
                    break
            return peor_valor, peor_mov

    def mejor_movimiento(self, tablero, jugador, profundidad=3):
        _, mov = self.minimax(tablero, profundidad, jugador, True, -math.inf, math.inf)
        return mov


# ==============================================================
# MAIN
# ==============================================================
if __name__ == "__main__":
    cliente = Lanzador(nombre="IA_EXPERTA")
    cliente.iniciar()
