# ==============================================================
# 🔄 VERSIÓN ADAPTADA A WEBSOCKET
# Solo se reemplazan las partes de socket TCP por websockets
# ==============================================================
import asyncio              # 🆕 agregado
import websockets            # 🆕 agregado
import json
import pygame
import numpy as np
import time
import threading             # se mantiene, usado por IA o interfaz

class Lanzador:
    def __init__(self, host="localhost", port=5555, nombre="IA1"):
        self.host = host
        self.port = port
        self.nombre = nombre
        self.ws = None        # 🆕 agregado (reemplaza self.socket)
        self.juego_activo = False
        self.color_jugador = None
        self.tablero = np.zeros((8, 8), dtype=int)
        self.turno_actual = 1

    # ==========================================================
    # 🔄 conexión WebSocket en lugar de socket TCP
    # ==========================================================
    async def conectar_servidor(self):  # 🔄 cambiado (era método normal)
        uri = f"wss://juegoothelloia.onrender.com"  # 🆕 URL Render (ajustar con tu dominio real)
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

                # Escuchar mensajes del servidor
                async for msg in websocket:   # 🔄 cambiado (antes socket.recv)
                    data = json.loads(msg)
                    self.procesar_mensaje(data)

        except Exception as e:
            print(f"❌ Error al conectar al servidor: {e}")

    # ==========================================================
    # 🔄 envío de mensajes por WebSocket
    # ==========================================================
    async def enviar_mensaje(self, mensaje):  # 🔄 cambiado (async)
        try:
            if self.ws:
                await self.ws.send(json.dumps(mensaje))
        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")

    # ==========================================================
    # 🔄 recepción: eliminamos hilo de lectura socket y usamos async for
    # ==========================================================
    def procesar_mensaje(self, data):  # se mantiene igual
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
            self.mostrar_tablero()
        elif tipo == "opponent_disconnected":
            print("⚠️  Oponente desconectado.")
        elif tipo == "move_response":
            print(data["message"])
        else:
            print("📩 Mensaje desconocido:", data)

    def mostrar_tablero(self):
        print("\n--- TABLERO ---")
        print(self.tablero)
        print(f"Turno del jugador: {self.turno_actual}")
        print("----------------\n")

    # ==========================================================
    # 🔄 nuevo método para ejecutar desde main con asyncio
    # ==========================================================
    def iniciar(self):  # 🔄 cambiado
        asyncio.run(self.conectar_servidor())  # 🆕 agregado


# ==============================================================
# 🔄 main adaptado a asyncio
# ==============================================================
if __name__ == "__main__":  # 🔄 cambiado
    cliente = Lanzador(nombre="IA1")  # o IA2, según corresponda
    cliente.iniciar()                 # 🔄 cambiado (antes conectar_servidor directo)
