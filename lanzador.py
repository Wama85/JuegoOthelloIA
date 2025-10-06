# ia_visual.py - Cliente IA con interfaz gráfica PyGame
import pygame
import sys
import numpy as np
import socket
import json
import threading
import time
import random
import copy

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


class OthelloAI:
    """IA para jugar Othello"""

    def __init__(self, difficulty='medium'):
        self.difficulty = difficulty
        self.position_weights = np.array([
            [100, -20,  10,   5,   5,  10, -20, 100],
            [-20, -50,  -2,  -2,  -2,  -2, -50, -20],
            [ 10,  -2,   5,   1,   1,   5,  -2,  10],
            [  5,  -2,   1,   0,   0,   1,  -2,   5],
            [  5,  -2,   1,   0,   0,   1,  -2,   5],
            [ 10,  -2,   5,   1,   1,   5,  -2,  10],
            [-20, -50,  -2,  -2,  -2,  -2, -50, -20],
            [100, -20,  10,   5,   5,  10, -20, 100]
        ])

    def choose_move(self, valid_moves, board, player_color):
        if not valid_moves:
            return None

        if self.difficulty == 'easy':
            return random.choice(valid_moves)
        elif self.difficulty == 'medium':
            return self.greedy_move(valid_moves, board, player_color)
        else:
            return self.minimax_move(valid_moves, board, player_color)

    def greedy_move(self, valid_moves, board, player_color):
        best_move = None
        best_score = -float('inf')

        for move in valid_moves:
            row, col = move
            temp_board = self.simulate_move(board, row, col, player_color)
            pieces_gained = np.sum(temp_board == player_color) - np.sum(board == player_color)
            position_value = self.position_weights[row][col]
            score = pieces_gained * 10 + position_value

            if score > best_score:
                best_score = score
                best_move = move

        return best_move

    def minimax_move(self, valid_moves, board, player_color, depth=3):
        best_move = None
        best_score = -float('inf')

        for move in valid_moves:
            row, col = move
            temp_board = self.simulate_move(board, row, col, player_color)
            score = self.minimax(temp_board, depth - 1, False, player_color, -float('inf'), float('inf'))

            if score > best_score:
                best_score = score
                best_move = move

        return best_move

    def minimax(self, board, depth, is_maximizing, player_color, alpha, beta):
        if depth == 0:
            return self.evaluate_board(board, player_color)

        opponent = 3 - player_color
        current_player = player_color if is_maximizing else opponent
        valid_moves = self.get_valid_moves_from_board(board, current_player)

        if not valid_moves:
            return self.evaluate_board(board, player_color)

        if is_maximizing:
            max_eval = -float('inf')
            for move in valid_moves:
                row, col = move
                temp_board = self.simulate_move(board, row, col, current_player)
                eval_score = self.minimax(temp_board, depth - 1, False, player_color, alpha, beta)
                max_eval = max(max_eval, eval_score)
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            for move in valid_moves:
                row, col = move
                temp_board = self.simulate_move(board, row, col, current_player)
                eval_score = self.minimax(temp_board, depth - 1, True, player_color, alpha, beta)
                min_eval = min(min_eval, eval_score)
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break
            return min_eval

    def evaluate_board(self, board, player_color):
        opponent = 3 - player_color
        player_pieces = np.sum(board == player_color)
        opponent_pieces = np.sum(board == opponent)
        player_position_value = np.sum((board == player_color) * self.position_weights)
        opponent_position_value = np.sum((board == opponent) * self.position_weights)
        player_mobility = len(self.get_valid_moves_from_board(board, player_color))
        opponent_mobility = len(self.get_valid_moves_from_board(board, opponent))

        score = (player_pieces - opponent_pieces) + \
                (player_position_value - opponent_position_value) * 2 + \
                (player_mobility - opponent_mobility) * 5
        return score

    def simulate_move(self, board, row, col, player):
        new_board = copy.deepcopy(board)
        new_board[row][col] = player

        opponent = 3 - player
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                      (0, 1), (1, -1), (1, 0), (1, 1)]

        for dr, dc in directions:
            if self.check_direction(new_board, row, col, dr, dc, player, opponent):
                self.flip_pieces(new_board, row, col, dr, dc, player, opponent)

        return new_board

    def check_direction(self, board, row, col, dr, dc, player, opponent):
        r, c = row + dr, col + dc
        found_opponent = False

        while 0 <= r < 8 and 0 <= c < 8:
            if board[r][c] == opponent:
                found_opponent = True
            elif board[r][c] == player:
                return found_opponent
            else:
                return False
            r += dr
            c += dc
        return False

    def flip_pieces(self, board, row, col, dr, dc, player, opponent):
        pieces_to_flip = []
        r, c = row + dr, col + dc

        while 0 <= r < 8 and 0 <= c < 8:
            if board[r][c] == opponent:
                pieces_to_flip.append((r, c))
            elif board[r][c] == player:
                for fr, fc in pieces_to_flip:
                    board[fr][fc] = player
                break
            else:
                break
            r += dr
            c += dc

    def get_valid_moves_from_board(self, board, player):
        valid_moves = []
        for row in range(8):
            for col in range(8):
                if board[row][col] == 0 and self.is_valid_move_on_board(board, row, col, player):
                    valid_moves.append([row, col])
        return valid_moves

    def is_valid_move_on_board(self, board, row, col, player):
        opponent = 3 - player
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                      (0, 1), (1, -1), (1, 0), (1, 1)]

        for dr, dc in directions:
            if self.check_direction(board, row, col, dr, dc, player, opponent):
                return True
        return False


class AIGameClient:
    def __init__(self, host='localhost', port=5555, difficulty='medium', think_time=1.5):
        self.host = host
        self.port = port
        self.socket = None
        self.player_color = None
        self.game_state = None
        self.connected = False
        self.connection_status = "Desconectado"
        self.waiting_for_opponent = True
        self.ai = OthelloAI(difficulty=difficulty)
        self.think_time = think_time
        self.difficulty_name = difficulty.upper()

        # Estado inicial del tablero
        self.initialize_default_board()

        # PyGame
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(f"IA Othello - {self.difficulty_name}")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 24)
        self.small_font = pygame.font.SysFont('Arial', 18)
        self.big_font = pygame.font.SysFont('Arial', 36, bold=True)

        # Tiempo para próximo movimiento
        self.next_move_time = None

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
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(0.5)
            self.connected = True
            self.connection_status = "Conectado"
            print("✅ ¡Conectado al servidor!")

            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            return True

        except Exception as e:
            self.connection_status = f"Error: {str(e)}"
            print(f"❌ {self.connection_status}")
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
        print(f"📨 Mensaje: {msg_type}")

        if msg_type == 'welcome':
            self.player_color = message['player_color']
            color_name = 'Negro' if self.player_color == 1 else 'Blanco'
            self.connection_status = f"IA {color_name} - {self.difficulty_name}"
            self.waiting_for_opponent = True
            print(f"🎯 Soy {color_name}")

        elif msg_type == 'waiting':
            self.waiting_for_opponent = True
            print("⏳ Esperando oponente...")

        elif msg_type == 'game_start':
            self.game_state = message['game_state']
            self.waiting_for_opponent = False
            print("🎮 ¡Juego iniciado!")
            self.schedule_next_move()

        elif msg_type == 'game_update':
            self.game_state = message['game_state']
            self.waiting_for_opponent = False
            print("📊 Tablero actualizado")
            self.schedule_next_move()

        elif msg_type == 'opponent_disconnected':
            self.waiting_for_opponent = True
            self.connection_status = "Oponente desconectado"
            print("⚠️ Oponente desconectado")

    def schedule_next_move(self):
        """Programa el próximo movimiento"""
        if (self.game_state and
                not self.game_state['game_over'] and
                self.game_state['current_player'] == self.player_color):
            self.next_move_time = time.time() + self.think_time

    def check_and_make_move(self):
        """Verifica si es momento de hacer un movimiento"""
        if self.next_move_time and time.time() >= self.next_move_time:
            self.next_move_time = None
            self.make_ai_move()

    def make_ai_move(self):
        """La IA hace un movimiento"""
        if not self.game_state or self.game_state['game_over']:
            return

        if self.game_state['current_player'] != self.player_color:
            return

        valid_moves = self.game_state.get('valid_moves', [])
        if not valid_moves:
            print("❌ Sin movimientos válidos")
            return

        print(f"🤔 IA pensando... ({len(valid_moves)} opciones)")

        board = np.array(self.game_state['board'])
        move = self.ai.choose_move(valid_moves, board, self.player_color)

        if move:
            row, col = move
            print(f"🎯 IA juega en ({row}, {col})")
            self.send_move(row, col)

    def send_move(self, row, col):
        message = {'type': 'move', 'row': row, 'col': col}
        try:
            message_str = json.dumps(message) + '\n'
            self.socket.send(message_str.encode('utf-8'))
        except Exception as e:
            print(f"❌ Error enviando: {e}")

    def draw_waiting_screen(self):
        self.screen.fill(BACKGROUND)

        # Tablero base
        for i in range(BOARD_SIZE + 1):
            pygame.draw.line(self.screen, BLACK, (0, i * CELL_SIZE), (WIDTH, i * CELL_SIZE), 2)
            pygame.draw.line(self.screen, BLACK, (i * CELL_SIZE, 0), (i * CELL_SIZE, HEIGHT), 2)

        # Fichas por defecto
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if self.default_board[row][col] != 0:
                    center_x = col * CELL_SIZE + CELL_SIZE // 2
                    center_y = row * CELL_SIZE + CELL_SIZE // 2
                    color = BLACK if self.default_board[row][col] == 1 else WHITE
                    pygame.draw.circle(self.screen, color, (center_x, center_y), DOT_RADIUS)

        # Overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))

        # Título
        title = self.big_font.render("OTHELLO IA", True, YELLOW)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        # Estado
        status_color = GREEN if self.connected else RED
        status = self.font.render(self.connection_status, True, status_color)
        self.screen.blit(status, (WIDTH // 2 - status.get_width() // 2, 180))

        if self.waiting_for_opponent:
            wait_text = self.big_font.render("ESPERANDO OPONENTE...", True, YELLOW)
            self.screen.blit(wait_text, (WIDTH // 2 - wait_text.get_width() // 2, 300))

    def draw_board(self):
        if not self.game_state:
            return

        self.screen.fill(BACKGROUND)

        # Tablero
        for i in range(BOARD_SIZE + 1):
            pygame.draw.line(self.screen, BLACK, (0, i * CELL_SIZE), (WIDTH, i * CELL_SIZE), 2)
            pygame.draw.line(self.screen, BLACK, (i * CELL_SIZE, 0), (i * CELL_SIZE, HEIGHT), 2)

        # Fichas
        board = self.game_state['board']
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if board[row][col] != 0:
                    center_x = col * CELL_SIZE + CELL_SIZE // 2
                    center_y = row * CELL_SIZE + CELL_SIZE // 2
                    color = BLACK if board[row][col] == 1 else WHITE
                    pygame.draw.circle(self.screen, color, (center_x, center_y), DOT_RADIUS)
                    pygame.draw.circle(self.screen, (100, 100, 100), (center_x, center_y), DOT_RADIUS, 2)

        # Info
        self.draw_game_info()

    def draw_game_info(self):
        if not self.game_state:
            return

        # Barra superior
        info_bg = pygame.Surface((WIDTH, 60))
        info_bg.set_alpha(200)
        info_bg.fill(BLACK)
        self.screen.blit(info_bg, (0, 0))

        # Título
        title_text = f"IA {self.difficulty_name}"
        if self.player_color:
            color_name = "NEGRO" if self.player_color == 1 else "BLANCO"
            title_text += f" ({color_name})"

        title_surface = self.font.render(title_text, True, YELLOW)
        self.screen.blit(title_surface, (20, 15))

        # Turno
        if self.game_state['game_over']:
            turn_text = "JUEGO TERMINADO"
            color = RED
        else:
            is_my_turn = self.game_state['current_player'] == self.player_color
            turn_text = "MI TURNO" if is_my_turn else "TURNO OPONENTE"
            color = GREEN if is_my_turn else BLUE

        turn_surface = self.small_font.render(turn_text, True, color)
        self.screen.blit(turn_surface, (20, 40))

        # Puntaje con texto claro
        scores = self.game_state['scores']
        score_text = f"Negro: {scores['black']}  Blanco: {scores['white']}"
        score_surface = self.font.render(score_text, True, WHITE)
        self.screen.blit(score_surface, (WIDTH - 250, 20))

        # Si el juego terminó, mostrar ganador
        if self.game_state['game_over']:
            self.draw_winner_screen(scores)

    def draw_winner_screen(self, scores):
        """Muestra el ganador en pantalla"""
        # Overlay semi-transparente
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # Determinar ganador
        if scores['black'] > scores['white']:
            winner_text = "¡GANA NEGRO!"
            winner_color = BLACK
            bg_color = WHITE
        elif scores['white'] > scores['black']:
            winner_text = "¡GANA BLANCO!"
            winner_color = WHITE
            bg_color = BLACK
        else:
            winner_text = "¡EMPATE!"
            winner_color = YELLOW
            bg_color = BLACK

        # Título grande
        winner_surface = self.big_font.render(winner_text, True, winner_color)
        winner_rect = winner_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80))

        # Fondo para el texto del ganador
        bg_rect = pygame.Rect(winner_rect.x - 20, winner_rect.y - 10,
                              winner_rect.width + 40, winner_rect.height + 20)
        pygame.draw.rect(self.screen, bg_color, bg_rect)
        pygame.draw.rect(self.screen, winner_color, bg_rect, 3)

        self.screen.blit(winner_surface, winner_rect)

        # Puntaje final
        score_text = f"Negro: {scores['black']}  -  Blanco: {scores['white']}"
        score_surface = self.big_font.render(score_text, True, WHITE)
        score_rect = score_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.screen.blit(score_surface, score_rect)

        # Diferencia de puntos
        diff = abs(scores['black'] - scores['white'])
        diff_text = f"Diferencia: {diff} fichas"
        diff_surface = self.font.render(diff_text, True, YELLOW)
        diff_rect = diff_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60))
        self.screen.blit(diff_surface, diff_rect)

        # Instrucción
        exit_text = "Presiona ESC para salir"
        exit_surface = self.small_font.render(exit_text, True, WHITE)
        exit_rect = exit_surface.get_rect(center=(WIDTH // 2, HEIGHT - 50))
        self.screen.blit(exit_surface, exit_rect)
    def run(self):
        if not self.connect():
            print("⚠️ No se pudo conectar")

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            # Verificar si debe hacer movimiento
            self.check_and_make_move()

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
    print("="*50)
    print("🤖 CLIENTE IA VISUAL - OTHELLO")
    print("="*50)

    host = input("Servidor [localhost]: ").strip() or 'localhost'
    port_input = input("Puerto [5555]: ").strip()
    port = int(port_input) if port_input.isdigit() else 5555

    print("\nDificultad:")
    print("1. Fácil (aleatorio)")
    print("2. Medio (codicioso)")
    print("3. Difícil (minimax)")

    diff_input = input("Selecciona [2]: ").strip()
    difficulty_map = {'1': 'easy', '2': 'medium', '3': 'hard', '': 'medium'}
    difficulty = difficulty_map.get(diff_input, 'medium')

    print(f"\n🚀 Iniciando IA {difficulty.upper()}...")
    client = AIGameClient(host, port, difficulty, think_time=1.5)
    client.run()