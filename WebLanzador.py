# ==============================================================
# VERSIÓN WEB-SOCKET + INTERFAZ PYGAME FUNCIONAL
# ==============================================================
import asyncio
import websockets
import json
import pygame
import numpy as np
import threading


class Lanzador:
    def __init__(self, host="wss://juegoothelloia.onrender.com", nombre="IA1"):
        self.host = host
        self.nombre = nombre
        self.ws = None
        self.juego_activo = False
        self.color_jugador = None
        self.tablero = np.zeros((8, 8), dtype=int)
        self.turno_actual = 1

        # Configuración visual
        self.celda = 75
        self.colores = {
            0: (0, 128, 0),     # verde del tablero
            1: (0, 0, 0),       # fichas negras
            2: (255, 255, 255)  # fichas blancas
        }

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

                # Enviar mensaje de conexión
                await self.enviar_mensaje({
                    "type": "join",
                    "name": self.nombre
                })

                # Escuchar mensajes
                async for msg in websocket:
                    data = json.loads(msg)
                    self.procesar_mensaje(data)

        except Exception as e:
            print(f"❌ Error al conectar al servidor: {e}")

    # ==========================================================
    # Envío de mensajes
    # ==========================================================
    async def enviar_mensaje(self, mensaje):
        try:
            if self.ws:
                await self.ws.send(json.dumps(mensaje))
        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")

    # ==========================================================
    # Procesar mensajes recibidos
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
        elif tipo == "opponent_disconnected":
            print("⚠️  Oponente desconectado.")
        elif tipo == "move_response":
            print(data["message"])
        else:
            print("📩 Mensaje desconocido:", data)

    # ==========================================================
    # Interfaz gráfica con Pygame
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

            # Dibujar tablero base
            screen.fill((0, 128, 0))
            for i in range(9):
                pygame.draw.line(screen, (0, 0, 0), (0, i * self.celda), (600, i * self.celda), 2)
                pygame.draw.line(screen, (0, 0, 0), (i * self.celda, 0), (i * self.celda, 600), 2)

            # Dibujar fichas
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
    # Inicio general (lanza Pygame + conexión WS)
    # ==========================================================
    def iniciar(self):
        threading.Thread(target=self.iniciar_interfaz, daemon=True).start()
        asyncio.run(self.conectar_servidor())


# ==============================================================
# MAIN
# ==============================================================
if __name__ == "__main__":
    cliente = Lanzador(nombre="IA1")
    cliente.iniciar()
