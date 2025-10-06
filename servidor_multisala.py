import socket
import json
import threading
import time
import numpy as np
import uuid

class OthelloGame:
    def __init__(self):
        self.board = np.zeros((8, 8), dtype=int)
        self.current_player = 1  # 1 = Negro, 2 = Blanco
        self.game_over = False

        # Configuración inicial
        self.board[3][3] = 2
        self.board[4][4] = 2
        self.board[3][4] = 1
        self.board[4][3] = 1

    def get_valid_moves(self, player):
        """Obtiene todos los movimientos válidos para un jugador"""
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

        opponent = 3 - player
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                      (0, 1), (1, -1), (1, 0), (1, 1)]

        for dr, dc in directions:
            if self.check_direction(row, col, dr, dc, player, opponent):
                return True
        return False

    def check_direction(self, row, col, dr, dc, player, opponent):
        """Verifica si hay fichas a voltear en una dirección"""
        r, c = row + dr, col + dc
        found_opponent = False

        while 0 <= r < 8 and 0 <= c < 8:
            if self.board[r][c] == opponent:
                found_opponent = True
            elif self.board[r][c] == player:
                return found_opponent
            else:
                return False
            r += dr
            c += dc
        return False

    def make_move(self, row, col, player):
        """Realiza un movimiento y voltea las fichas"""
        if not self.is_valid_move(row, col, player):
            return False

        self.board[row][col] = player
        opponent = 3 - player
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                      (0, 1), (1, -1), (1, 0), (1, 1)]

        for dr, dc in directions:
            if self.check_direction(row, col, dr, dc, player, opponent):
                self.flip_pieces(row, col, dr, dc, player, opponent)

        return True

    def flip_pieces(self, row, col, dr, dc, player, opponent):
        """Voltea las fichas en una dirección"""
        pieces_to_flip = []
        r, c = row + dr, col + dc

        while 0 <= r < 8 and 0 <= c < 8:
            if self.board[r][c] == opponent:
                pieces_to_flip.append((r, c))
            elif self.board[r][c] == player:
                for fr, fc in pieces_to_flip:
                    self.board[fr][fc] = player
                break
            else:
                break
            r += dr
            c += dc

    def get_scores(self):
        """Calcula el puntaje actual"""
        black = np.sum(self.board == 1)
        white = np.sum(self.board == 2)
        return {'black': int(black), 'white': int(white)}

    def check_game_over(self):
        """Verifica si el juego ha terminado"""
        valid_moves_p1 = self.get_valid_moves(1)
        valid_moves_p2 = self.get_valid_moves(2)

        if len(valid_moves_p1) == 0 and len(valid_moves_p2) == 0:
            self.game_over = True
            return True
        return False

    def get_game_state(self):
        """Retorna el estado actual del juego"""
        return {
            'board': self.board.tolist(),
            'current_player': self.current_player,
            'valid_moves': self.get_valid_moves(self.current_player),
            'game_over': self.game_over,
            'scores': self.get_scores()
        }


class GameRoom:
    """Representa una sala de juego con 2 jugadores"""
    def __init__(self, room_id):
        self.room_id = room_id
        self.game = OthelloGame()
        self.players = []  # Máximo 2 jugadores
        self.started = False

    def add_player(self, client_handler):
        """Agrega un jugador a la sala"""
        if len(self.players) < 2:
            self.players.append(client_handler)
            client_handler.room = self
            client_handler.player_color = len(self.players)
            return True
        return False

    def remove_player(self, client_handler):
        """Remueve un jugador de la sala"""
        if client_handler in self.players:
            self.players.remove(client_handler)
            client_handler.room = None
            return True
        return False

    def is_full(self):
        """Verifica si la sala está llena"""
        return len(self.players) >= 2

    def is_empty(self):
        """Verifica si la sala está vacía"""
        return len(self.players) == 0

    def start_game(self):
        """Inicia el juego en esta sala"""
        if len(self.players) == 2 and not self.started:
            self.started = True
            game_start_msg = {
                'type': 'game_start',
                'message': '¡Juego iniciado!',
                'game_state': self.game.get_game_state()
            }

            for player in self.players:
                player.send_message(game_start_msg)

            print(f"🎮 Sala {self.room_id[:8]} - Juego iniciado")
            return True
        return False

    def broadcast(self, message, exclude=None):
        """Envía un mensaje a todos los jugadores de la sala"""
        for player in self.players:
            if player != exclude:
                player.send_message(message)

    def handle_move(self, client_handler, row, col):
        """Procesa un movimiento en esta sala"""
        if not self.started:
            return False

        # Verificar turno
        if client_handler.player_color != self.game.current_player:
            response = {
                'type': 'move_response',
                'success': False,
                'message': 'No es tu turno'
            }
            client_handler.send_message(response)
            return False

        # Intentar hacer el movimiento
        if self.game.make_move(row, col, client_handler.player_color):
            print(f"✅ Sala {self.room_id[:8]} - Jugador {client_handler.player_color} jugó en ({row}, {col})")

            # Cambiar turno
            self.game.current_player = 3 - self.game.current_player

            # Verificar si hay movimientos válidos
            valid_moves = self.game.get_valid_moves(self.game.current_player)
            if len(valid_moves) == 0:
                print(f"⚠️ Sala {self.room_id[:8]} - Jugador {self.game.current_player} sin movimientos, pasando turno")
                self.game.current_player = 3 - self.game.current_player
                valid_moves = self.game.get_valid_moves(self.game.current_player)
                if len(valid_moves) == 0:
                    print(f"🏁 Sala {self.room_id[:8]} - ¡Juego terminado!")
                    self.game.game_over = True

            # Enviar actualización a ambos jugadores
            update_msg = {
                'type': 'game_update',
                'game_state': self.game.get_game_state()
            }

            self.broadcast(update_msg)

            # Respuesta al cliente que hizo el movimiento
            response = {
                'type': 'move_response',
                'success': True,
                'message': 'Movimiento realizado'
            }
            client_handler.send_message(response)
            return True
        else:
            response = {
                'type': 'move_response',
                'success': False,
                'message': 'Movimiento inválido'
            }
            client_handler.send_message(response)
            return False


class ClientHandler:
    def __init__(self, socket, address, server):
        self.socket = socket
        self.address = address
        self.server = server
        self.player_color = None
        self.room = None
        self.active = True

    def send_message(self, message):
        """Envía un mensaje JSON al cliente"""
        try:
            message_str = json.dumps(message) + '\n'
            self.socket.send(message_str.encode('utf-8'))
            return True
        except Exception as e:
            print(f"❌ Error enviando mensaje a {self.address}: {e}")
            return False

    def receive_messages(self):
        """Recibe mensajes del cliente"""
        buffer = ""
        while self.active:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    print(f"📭 Cliente {self.address} cerró conexión")
                    break

                buffer += data
                while '\n' in buffer:
                    message_str, buffer = buffer.split('\n', 1)
                    if message_str.strip():
                        try:
                            message = json.loads(message_str)
                            self.handle_message(message)
                        except json.JSONDecodeError as e:
                            print(f"❌ Error decodificando JSON: {e}")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"❌ Error recibiendo mensajes de {self.address}: {e}")
                break

        self.disconnect()

    def handle_message(self, message):
        """Procesa mensajes del cliente"""
        msg_type = message.get('type')

        if msg_type == 'move':
            row = message.get('row')
            col = message.get('col')
            if self.room:
                self.room.handle_move(self, row, col)

    def disconnect(self):
        """Desconecta al cliente"""
        self.active = False
        try:
            self.socket.close()
        except:
            pass
        self.server.remove_client(self)


class OthelloServerMultiRoom:
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = []
        self.rooms = {}  # {room_id: GameRoom}
        self.waiting_players = []  # Jugadores esperando emparejamiento
        self.running = False
        self.lock = threading.Lock()

    def start(self):
        """Inicia el servidor"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(100)  # Soportar muchas conexiones
        self.running = True

        print(f"🎮 Servidor Othello Multi-Sala")
        print(f"📡 Iniciado en {self.host}:{self.port}")
        print(f"♾️  Soporta partidas ilimitadas simultáneas")
        print(f"⏳ Esperando jugadores...")

        accept_thread = threading.Thread(target=self.accept_clients)
        accept_thread.daemon = True
        accept_thread.start()

        # Thread para mostrar estadísticas
        stats_thread = threading.Thread(target=self.show_stats)
        stats_thread.daemon = True
        stats_thread.start()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo servidor...")
            self.stop()

    def accept_clients(self):
        """Acepta conexiones de clientes"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                client_socket.settimeout(0.5)

                print(f"✅ Cliente conectado: {address}")

                client_handler = ClientHandler(client_socket, address, self)

                with self.lock:
                    self.clients.append(client_handler)

                # Intentar emparejar inmediatamente
                self.match_player(client_handler)

                # Iniciar hilo de recepción
                receive_thread = threading.Thread(target=client_handler.receive_messages)
                receive_thread.daemon = True
                receive_thread.start()

            except Exception as e:
                if self.running:
                    print(f"❌ Error aceptando cliente: {e}")

    def match_player(self, client_handler):
        """Empareja a un jugador (matchmaking)"""
        with self.lock:
            # Buscar una sala disponible
            available_room = None
            for room_id, room in self.rooms.items():
                if not room.is_full() and not room.started:
                    available_room = room
                    break

            if available_room:
                # Agregar a sala existente
                available_room.add_player(client_handler)

                # Enviar mensaje de bienvenida
                welcome_msg = {
                    'type': 'welcome',
                    'message': f'Bienvenido! Eres el jugador {"Negro" if client_handler.player_color == 1 else "Blanco"}',
                    'player_color': client_handler.player_color
                }
                client_handler.send_message(welcome_msg)

                print(f"🎯 Cliente {client_handler.address} asignado a sala {available_room.room_id[:8]} como jugador {client_handler.player_color}")

                # Si la sala está llena, iniciar juego
                if available_room.is_full():
                    available_room.start_game()
                else:
                    waiting_msg = {
                        'type': 'waiting',
                        'message': 'Esperando oponente...'
                    }
                    client_handler.send_message(waiting_msg)
            else:
                # Crear nueva sala
                new_room_id = str(uuid.uuid4())
                new_room = GameRoom(new_room_id)
                self.rooms[new_room_id] = new_room

                new_room.add_player(client_handler)

                # Enviar mensaje de bienvenida
                welcome_msg = {
                    'type': 'welcome',
                    'message': f'Bienvenido! Eres el jugador Negro',
                    'player_color': 1
                }
                client_handler.send_message(welcome_msg)

                waiting_msg = {
                    'type': 'waiting',
                    'message': 'Esperando oponente...'
                }
                client_handler.send_message(waiting_msg)

                print(f"🆕 Nueva sala {new_room_id[:8]} creada para {client_handler.address}")

    def remove_client(self, client_handler):
        """Remueve un cliente desconectado"""
        with self.lock:
            if client_handler in self.clients:
                self.clients.remove(client_handler)
                print(f"📤 Cliente {client_handler.address} removido")

            # Si estaba en una sala, notificar al otro jugador
            if client_handler.room:
                room = client_handler.room
                room.remove_player(client_handler)

                # Notificar a los otros jugadores de la sala
                disconnect_msg = {
                    'type': 'opponent_disconnected',
                    'message': 'Tu oponente se desconectó'
                }
                room.broadcast(disconnect_msg, exclude=client_handler)

                # Si la sala quedó vacía, eliminarla
                if room.is_empty():
                    del self.rooms[room.room_id]
                    print(f"🗑️  Sala {room.room_id[:8]} eliminada (vacía)")

    def show_stats(self):
        """Muestra estadísticas periódicamente"""
        while self.running:
            time.sleep(30)  # Cada 30 segundos
            with self.lock:
                active_games = sum(1 for room in self.rooms.values() if room.started)
                waiting_rooms = sum(1 for room in self.rooms.values() if not room.started)
                total_clients = len(self.clients)

                print(f"\n📊 ESTADÍSTICAS:")
                print(f"   👥 Clientes conectados: {total_clients}")
                print(f"   🎮 Partidas activas: {active_games}")
                print(f"   ⏳ Salas esperando: {waiting_rooms}")
                print(f"   🏠 Salas totales: {len(self.rooms)}\n")

    def stop(self):
        """Detiene el servidor"""
        self.running = False
        for client in self.clients[:]:
            client.disconnect()
        if self.server_socket:
            self.server_socket.close()
        print("👋 Servidor detenido")


if __name__ == "__main__":
    print("=" * 50)
    print("🎮 SERVIDOR OTHELLO MULTI-SALA")
    print("=" * 50)
    print("Soporta múltiples partidas simultáneas")
    print("Matchmaking automático")
    print("=" * 50)

    port_input = input("\nPuerto [5555]: ").strip()
    port = int(port_input) if port_input.isdigit() else 5555

    server = OthelloServerMultiRoom(host='0.0.0.0', port=port)
    server.start()