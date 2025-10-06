import socket
import threading
import asyncio
import websockets
import json
import numpy as np
import time

class OthelloGame:
    def __init__(self):
        self.board = np.zeros((8, 8), dtype=int)
        self.current_player = 1  # 1 = Negro, 2 = Blanco
        self.game_over = False
        self.winner = None

        # Configuración inicial del tablero
        self.board[3][3] = 2  # Blanco
        self.board[4][4] = 2  # Blanco
        self.board[3][4] = 1  # Negro
        self.board[4][3] = 1  # Negro

    def get_valid_moves(self, player):
        """Retorna lista de movimientos válidos para el jugador"""
        valid_moves = []
        for row in range(8):
            for col in range(8):
                if self.is_valid_move(row, col, player):
                    valid_moves.append([row, col])
        return valid_moves

    def is_valid_move(self, row, col, player):
        """Verifica si un movimiento es válido"""
        if self.board[row][col] != 0:
            return False

        opponent = 3 - player  # Si player=1 entonces opponent=2, viceversa
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

        for dr, dc in directions:
            r, c = row + dr, col + dc
            found_opponent = False

            while 0 <= r < 8 and 0 <= c < 8:
                if self.board[r][c] == opponent:
                    found_opponent = True
                    r += dr
                    c += dc
                elif self.board[r][c] == player and found_opponent:
                    return True
                else:
                    break

        return False

    def make_move(self, row, col, player):
        """Realiza un movimiento y voltea las fichas"""
        if not self.is_valid_move(row, col, player):
            return False

        self.board[row][col] = player
        opponent = 3 - player
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

        for dr, dc in directions:
            r, c = row + dr, col + dc
            pieces_to_flip = []

            while 0 <= r < 8 and 0 <= c < 8:
                if self.board[r][c] == opponent:
                    pieces_to_flip.append((r, c))
                    r += dr
                    c += dc
                elif self.board[r][c] == player:
                    for flip_r, flip_c in pieces_to_flip:
                        self.board[flip_r][flip_c] = player
                    break
                else:
                    break

        return True

    def get_scores(self):
        """Retorna los puntajes de cada jugador"""
        black = np.sum(self.board == 1)
        white = np.sum(self.board == 2)
        return {'black': int(black), 'white': int(white)}

    def check_game_over(self):
        """Verifica si el juego ha terminado"""
        valid_moves_p1 = self.get_valid_moves(1)
        valid_moves_p2 = self.get_valid_moves(2)

        if not valid_moves_p1 and not valid_moves_p2:
            self.game_over = True
            scores = self.get_scores()
            if scores['black'] > scores['white']:
                self.winner = 1
            elif scores['white'] > scores['black']:
                self.winner = 2
            else:
                self.winner = 0  # Empate
            return True

        return False

    def get_state(self):
        """Retorna el estado completo del juego"""
        return {
            'board': self.board.tolist(),
            'current_player': int(self.current_player),
            'valid_moves': self.get_valid_moves(self.current_player),
            'scores': self.get_scores(),
            'game_over': self.game_over,
            'winner': self.winner
        }


class GameServer:
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = []
        self.game = None
        self.player_colors = {}  # socket: color
        self.running = False

    def start(self):
        """Inicia el servidor"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(2)
        client_socket, address = self.server_socket.accept()
        self.running = True

        print(f"🎮 Servidor Othello iniciado en {self.host}:{self.port}")
        print("⏳ Esperando jugadores...")

        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"✅ Cliente conectado desde {address}")

                if len(self.clients) < 2:
                    self.clients.append(client_socket)
                    player_color = len(self.clients)  # 1 o 2
                    self.player_colors[client_socket] = player_color

                    # Enviar mensaje de bienvenida
                    welcome_msg = {
                        'type': 'welcome',
                        'player_color': player_color,
                        'message': f'Eres el jugador {"Negro" if player_color == 1 else "Blanco"}'
                    }
                    self.send_message(client_socket, welcome_msg)

                    if len(self.clients) == 1:
                        # Primer jugador, enviar mensaje de espera
                        waiting_msg = {
                            'type': 'waiting',
                            'message': 'Esperando segundo jugador...'
                        }
                        self.send_message(client_socket, waiting_msg)

                    elif len(self.clients) == 2:
                        # Segundo jugador conectado, iniciar juego
                        print("🎯 ¡Dos jugadores conectados! Iniciando juego...")
                        self.start_game()

                    # Iniciar hilo para manejar mensajes del cliente
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                else:
                    # Ya hay 2 jugadores
                    reject_msg = {
                        'type': 'error',
                        'message': 'El servidor ya tiene 2 jugadores'
                    }
                    self.send_message(client_socket, reject_msg)
                    client_socket.close()

            except Exception as e:
                print(f"❌ Error aceptando cliente: {e}")
                break

    def start_game(self):
        """Inicia una nueva partida"""
        self.game = OthelloGame()

        # Enviar estado inicial a ambos jugadores
        game_start_msg = {
            'type': 'game_start',
            'message': '¡Juego iniciado!',
            'game_state': self.game.get_state()
        }

        for client in self.clients:
            self.send_message(client, game_start_msg)

        print("🎮 Juego iniciado")
        print(f"🎯 Turno del jugador {self.game.current_player}")

    def handle_client(self, client_socket):
        """Maneja mensajes de un cliente"""
        buffer = ""

        while self.running:
            try:
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    print("🔌 Cliente desconectado")
                    self.handle_disconnect(client_socket)
                    break

                buffer += data
                while '\n' in buffer:
                    message_str, buffer = buffer.split('\n', 1)
                    if message_str.strip():
                        try:
                            message = json.loads(message_str)
                            self.process_message(client_socket, message)
                        except json.JSONDecodeError as e:
                            print(f"❌ Error decodificando JSON: {e}")

            except Exception as e:
                print(f"❌ Error manejando cliente: {e}")
                self.handle_disconnect(client_socket)
                break

    def process_message(self, client_socket, message):
        """Procesa un mensaje del cliente"""
        msg_type = message.get('type')

        if msg_type == 'move':
            self.handle_move(client_socket, message)

    def handle_move(self, client_socket, message):
        """Maneja un movimiento de un jugador"""
        if not self.game or self.game.game_over:
            response = {
                'type': 'move_response',
                'success': False,
                'message': 'El juego no está activo'
            }
            self.send_message(client_socket, response)
            return

        player_color = self.player_colors.get(client_socket)

        if player_color != self.game.current_player:
            response = {
                'type': 'move_response',
                'success': False,
                'message': 'No es tu turno'
            }
            self.send_message(client_socket, response)
            return

        row = message.get('row')
        col = message.get('col')

        print(f"📥 Movimiento recibido del jugador {player_color}: ({row}, {col})")

        if self.game.make_move(row, col, player_color):
            print(f"✅ Movimiento válido ejecutado")

            # Responder al jugador que hizo el movimiento
            response = {
                'type': 'move_response',
                'success': True,
                'message': 'Movimiento exitoso'
            }
            self.send_message(client_socket, response)

            # Cambiar turno
            self.game.current_player = 3 - self.game.current_player

            # Verificar si el siguiente jugador tiene movimientos válidos
            valid_moves = self.game.get_valid_moves(self.game.current_player)
            if not valid_moves and not self.game.check_game_over():
                # El jugador actual no tiene movimientos, pasar turno
                print(f"⏭️  Jugador {self.game.current_player} sin movimientos, pasando turno")
                self.game.current_player = 3 - self.game.current_player

            # Verificar fin del juego
            self.game.check_game_over()

            # Enviar actualización a ambos jugadores
            update_msg = {
                'type': 'game_update',
                'game_state': self.game.get_state()
            }

            for client in self.clients:
                self.send_message(client, update_msg)

            if self.game.game_over:
                print(f"🏁 Juego terminado - Ganador: {self.game.winner}")
        else:
            print(f"❌ Movimiento inválido")
            response = {
                'type': 'move_response',
                'success': False,
                'message': 'Movimiento inválido'
            }
            self.send_message(client_socket, response)

    def handle_disconnect(self, client_socket):
        """Maneja la desconexión de un cliente"""
        if client_socket in self.clients:
            self.clients.remove(client_socket)

            # Notificar al otro jugador
            disconnect_msg = {
                'type': 'opponent_disconnected',
                'message': 'Tu oponente se ha desconectado'
            }

            for client in self.clients:
                self.send_message(client, disconnect_msg)

            # Reiniciar el juego
            self.game = None
            self.player_colors = {}

            print("⚠️  Cliente desconectado, esperando nuevos jugadores...")

    def send_message(self, client_socket, message):
        """Envía un mensaje a un cliente"""
        try:
            message_str = json.dumps(message) + '\n'
            client_socket.send(message_str.encode('utf-8'))
        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")

    def stop(self):
        """Detiene el servidor"""
        self.running = False
        for client in self.clients:
            client.close()
        if self.server_socket:
            self.server_socket.close()
        print("🛑 Servidor detenido")


if __name__ == "__main__":
    import os

    print("=" * 50)
    print("🎮 SERVIDOR OTHELLO ")
    print("=" * 50)

    # Render define el puerto en la variable de entorno PORT
    port = int(os.environ.get("PORT", 5555))

    server = GameServer(host="0.0.0.0", port=port)

    try:
        server.start()
    except KeyboardInterrupt:
        print("\n⏹️  Deteniendo servidor...")
        server.stop()
