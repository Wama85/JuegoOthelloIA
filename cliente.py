# cliente_simplificado.py
import pygame
import sys
import numpy as np
import socket
import json
import threading
import time

# Constantes
WIDTH, HEIGHT = 800, 800
BOARD_SIZE = 8
CELL_SIZE = WIDTH // BOARD_SIZE
DOT_RADIUS = CELL_SIZE // 2 - 5
HIGHLIGHT_RADIUS = CELL_SIZE // 2 - 10

# Colores
BACKGROUND = (0, 128, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
HIGHLIGHT = (255, 255, 0, 100)


class GameClient:
    def __init__(self, host='localhost', port=5555):
        self.host = host
        self.port = port
        self.socket = None
        self.player_color = None
        self.game_state = None
        self.connected = False
        self.connection_status = "Desconectado"
        self.last_error = ""
        self.waiting_for_opponent = True

        # Estado inicial del tablero
        self.initialize_default_board()

        # PyGame
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Sitemas Inteligentes - Cliente")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 24)
        self.small_font = pygame.font.SysFont('Arial', 18)
        self.big_font = pygame.font.SysFont('Arial', 36, bold=True)

        # Logo
        self.logo = pygame.image.load("intro.png")
        self.logo = pygame.transform.scale(self.logo, (80, 80))


    def initialize_default_board(self):
        self.default_board = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
        mid = BOARD_SIZE // 2
        self.default_board[mid - 1][mid - 1] = 2
        self.default_board[mid][mid] = 2
        self.default_board[mid - 1][mid] = 1
        self.default_board[mid][mid - 1] = 1

    def connect(self):
        try:
            self.connection_status = "Conectando..."
            self.last_error = ""

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(0.5)

            self.connected = True
            self.connection_status = "Conectado al servidor"
            print("✅ ¡Conectado al servidor!")

            # Iniciar hilo para recibir mensajes
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()

            return True

        except Exception as e:
            self.last_error = f"Error de conexión: {str(e)}"
            self.connection_status = "Error de conexión"
            print(f"❌ {self.last_error}")
            return False

    def receive_messages(self):
        buffer = ""
        while self.connected:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    print("📭 Servidor cerró la conexión")
                    self.connected = False
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
                print(f"❌ Error recibiendo mensajes: {e}")
                self.connected = False
                break

    def handle_message(self, message):
        msg_type = message.get('type')
        print(f"📨 Mensaje recibido del servidor: {msg_type}")

        if msg_type == 'welcome':
            self.player_color = message['player_color']
            self.connection_status = f"Jugador {'Negro' if self.player_color == 1 else 'Blanco'}"
            self.waiting_for_opponent = True
            print(f"🎯 {message['message']}")

        elif msg_type == 'waiting':
            self.waiting_for_opponent = True
            print("⏳ " + message['message'])

        elif msg_type == 'game_start':
            self.game_state = message['game_state']
            self.waiting_for_opponent = False
            print("🎮 ¡Juego iniciado!")
            print(f"📊 Tablero recibido - Turno actual: {self.game_state['current_player']}")
            print(f"🎯 Movimientos válidos: {self.game_state['valid_moves']}")

        elif msg_type == 'game_update':
            self.game_state = message['game_state']
            self.waiting_for_opponent = False
            print("🔄 Juego actualizado")
            print(f"🎯 Movimientos válidos: {len(self.game_state['valid_moves'])} movimientos")

        elif msg_type == 'move_response':
            print(f"📢 Respuesta de movimiento: {message['message']}")
            if not message['success']:
                print(f"❌ Movimiento fallido: {message['message']}")

        elif msg_type == 'opponent_disconnected':
            self.waiting_for_opponent = True
            self.connection_status = "Oponente desconectado"
            print("⚠️ " + message['message'])

    def send_message(self, message):
        if not self.connected:
            print("❌ No conectado, no se puede enviar mensaje")
            return False

        try:
            message_str = json.dumps(message) + '\n'
            self.socket.send(message_str.encode('utf-8'))
            print(f"📤 Mensaje enviado: {message['type']}")
            return True
        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")
            self.connected = False
            return False

    def send_move(self, row, col):
        message = {'type': 'move', 'row': row, 'col': col}
        return self.send_message(message)

    def draw_waiting_screen(self):
        self.screen.fill(BACKGROUND)

        # Dibujar tablero base
        for i in range(BOARD_SIZE + 1):
            pygame.draw.line(self.screen, BLACK, (0, i * CELL_SIZE), (WIDTH, i * CELL_SIZE), 2)
            pygame.draw.line(self.screen, BLACK, (i * CELL_SIZE, 0), (i * CELL_SIZE, HEIGHT), 2)

        # Dibujar fichas por defecto
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if self.default_board[row][col] != 0:
                    center_x = col * CELL_SIZE + CELL_SIZE // 2
                    center_y = row * CELL_SIZE + CELL_SIZE // 2
                    color = BLACK if self.default_board[row][col] == 1 else WHITE
                    pygame.draw.circle(self.screen, color, (center_x, center_y), DOT_RADIUS)

        # Overlay de espera
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))

        # Textos
        title = self.big_font.render("OTHELLO", True, WHITE)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        status_color = GREEN if self.connected else RED
        status = self.font.render(self.connection_status, True, status_color)
        self.screen.blit(status, (WIDTH // 2 - status.get_width() // 2, 180))

        if self.player_color:
            player_text = f"Eres: {'NEGRO' if self.player_color == 1 else 'BLANCO'}"
            player_surface = self.font.render(player_text, True, YELLOW)
            self.screen.blit(player_surface, (WIDTH // 2 - player_surface.get_width() // 2, 220))

        if self.waiting_for_opponent:
            wait_text = self.big_font.render("ESPERANDO OPONENTE...", True, YELLOW)
            self.screen.blit(wait_text, (WIDTH // 2 - wait_text.get_width() // 2, 300))
        else:
            ready_text = self.big_font.render("¡LISTO PARA JUGAR!", True, GREEN)
            self.screen.blit(ready_text, (WIDTH // 2 - ready_text.get_width() // 2, 300))

        # Instrucciones
        instructions = [
            "Presiona R para reconectar" if not self.connected else "",
            "Presiona ESC para salir"
        ]
        y_pos = 400
        for line in instructions:
            if line:
                text = self.small_font.render(line, True, WHITE)
                self.screen.blit(text, (WIDTH // 2 - text.get_width() // 2, y_pos))
                y_pos += 30

    def draw_board(self):
        if not self.game_state:
            return

        self.screen.fill(BACKGROUND)

        # Dibujar tablero
        for i in range(BOARD_SIZE + 1):
            pygame.draw.line(self.screen, BLACK, (0, i * CELL_SIZE), (WIDTH, i * CELL_SIZE), 2)
            pygame.draw.line(self.screen, BLACK, (i * CELL_SIZE, 0), (i * CELL_SIZE, HEIGHT), 2)

        # Dibujar fichas
        board = self.game_state['board']
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if board[row][col] != 0:
                    center_x = col * CELL_SIZE + CELL_SIZE // 2
                    center_y = row * CELL_SIZE + CELL_SIZE // 2
                    color = BLACK if board[row][col] == 1 else WHITE
                    pygame.draw.circle(self.screen, color, (center_x, center_y), DOT_RADIUS)
                    pygame.draw.circle(self.screen, (100, 100, 100), (center_x, center_y), DOT_RADIUS, 2)

        # Resaltar movimientos válidos (solo si es tu turno)
        if (not self.game_state['game_over'] and
                self.game_state['current_player'] == self.player_color and
                'valid_moves' in self.game_state):

            valid_moves = self.game_state['valid_moves']
            print(f"🎯 Dibujando {len(valid_moves)} movimientos válidos")

            for move in valid_moves:
                # Asegurarse de que el movimiento tenga el formato correcto
                if isinstance(move, list) and len(move) == 2:
                    row, col = move
                elif isinstance(move, tuple) and len(move) == 2:
                    row, col = move
                else:
                    continue

                center_x = col * CELL_SIZE + CELL_SIZE // 2
                center_y = row * CELL_SIZE + CELL_SIZE // 2

                # Dibujar círculo de highlight
                highlight_surface = pygame.Surface((HIGHLIGHT_RADIUS * 2, HIGHLIGHT_RADIUS * 2), pygame.SRCALPHA)
                pygame.draw.circle(highlight_surface, HIGHLIGHT, (HIGHLIGHT_RADIUS, HIGHLIGHT_RADIUS), HIGHLIGHT_RADIUS)
                self.screen.blit(highlight_surface, (center_x - HIGHLIGHT_RADIUS, center_y - HIGHLIGHT_RADIUS))

                # Dibujar punto pequeño en el centro para mejor visibilidad
                pygame.draw.circle(self.screen, (255, 0, 0), (center_x, center_y), 3)

        # Información del juego
        self.draw_game_info()

    def draw_game_info(self):
        font = pygame.font.SysFont('Arial', 28, bold=True)
        if not self.game_state:
            return

        # Barra de información
        info_bg = pygame.Surface((WIDTH, 60))
        info_bg.set_alpha(200)
        info_bg.fill(BLACK)
        self.screen.blit(info_bg, (0, 0))

        # Turno actual
        logo_text = "Hello class, I wanna play a game!"
        if self.game_state['game_over']:
            turn_text = "JUEGO TERMINADO"
            color = RED
        else:
            is_my_turn = self.game_state['current_player'] == self.player_color
            turn_text = "TU TURNO" if is_my_turn else "TURNO OPONENTE"
            color = GREEN if is_my_turn else BLUE

        turn_surface = self.font.render(turn_text, True, color)
        logo_surface = font.render(logo_text, True, RED)

        #self.screen.blit(turn_surface, (WIDTH // 2 - turn_surface.get_width() // 2, 20))
        self.screen.blit(turn_surface, (20, 50))
        self.screen.blit(logo_surface, (20, 15))


        # Puntuación
        scores = self.game_state['scores']
        score_text = f"Negro: {scores['black']}  Blanco: {scores['white']}"
        score_surface = self.small_font.render(score_text, True, WHITE)
        self.screen.blit(score_surface, (WIDTH - 200, 25))

        # Información de movimientos válidos
        if not self.game_state['game_over'] and self.game_state['current_player'] == self.player_color:
            valid_count = len(self.game_state['valid_moves']) if 'valid_moves' in self.game_state else 0
            moves_text = f"Movimientos válidos: {valid_count}"
            moves_surface = self.small_font.render(moves_text, True, YELLOW)
            self.screen.blit(moves_surface, (10, 25))

    def handle_click(self, pos):
        if not self.connected or self.waiting_for_opponent or not self.game_state:
            print("❌ No se puede hacer movimiento ahora")
            return

        if self.game_state['game_over']:
            print("❌ Juego terminado")
            return

        if self.game_state['current_player'] != self.player_color:
            print("❌ No es tu turno")
            return

        col = pos[0] // CELL_SIZE
        row = pos[1] // CELL_SIZE

        print(f"🎯 Click en posición: ({row}, {col})")

        if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
            # Verificar si el movimiento es válido
            valid_moves = self.game_state.get('valid_moves', [])
            print(f"🎯 Movimientos válidos disponibles: {valid_moves}")

            # Convertir el movimiento clickeado a formato comparable
            clicked_move = (row, col)
            print(f"🎯 Movimiento clickeado: {clicked_move}")

            # Verificar si el movimiento está en la lista de movimientos válidos
            is_valid = False
            for move in valid_moves:
                # Asegurarse de que el movimiento tenga el formato correcto para comparar
                if isinstance(move, list) and len(move) == 2:
                    move_tuple = (move[0], move[1])
                elif isinstance(move, tuple) and len(move) == 2:
                    move_tuple = move
                else:
                    continue

                if move_tuple == clicked_move:
                    is_valid = True
                    break

            if is_valid:
                print(f"✅ Movimiento válido en ({row}, {col}), enviando al servidor...")
                self.send_move(row, col)
            else:
                print(f"❌ Movimiento inválido en ({row}, {col})")
                print(f"   Movimiento clickeado: {clicked_move}")
                print(f"   Movimientos válidos: {valid_moves}")
        else:
            print(f"❌ Posición fuera del tablero: ({row}, {col})")

    def run(self):
        if not self.connect():
            print("⚠️ No se pudo conectar al servidor")

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r and not self.connected:
                        print("🔄 Intentando reconectar...")
                        self.connect()

            # Dibujar
            if self.connected and self.game_state and not self.waiting_for_opponent:
                self.draw_board()
            else:
                self.draw_waiting_screen()

            pygame.display.flip()
            self.clock.tick(60)

        if self.socket:
            self.socket.close()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    print("=== 🎮 CLIENTE  ===")
    host = input("Servidor [localhost]: ").strip() or 'localhost'
    port_input = input("Puerto [5555]: ").strip()
    port = int(port_input) if port_input.isdigit() else 5555

    client = GameClient(host, port)
    client.run()