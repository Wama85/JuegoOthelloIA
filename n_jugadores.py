# ia_n_jugadores.py - IA para Othello N jugadores
import pygame
import sys
import numpy as np
import socket
import json
import threading
import time
import random
import copy

# Constantes (igual que cliente_n_jugadores.py)
WIDTH, HEIGHT = 800, 850
BOARD_SIZE = 8
CELL_SIZE = 800 // BOARD_SIZE
DOT_RADIUS = CELL_SIZE // 2 - 5

BACKGROUND = (0, 128, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
ORANGE = (255, 165, 0)

PLAYER_COLORS = [BLACK, WHITE, RED, BLUE, YELLOW, CYAN, MAGENTA, ORANGE]
PLAYER_NAMES = ["Negro", "Blanco", "Rojo", "Azul", "Amarillo", "Cyan", "Magenta", "Naranja"]


class OthelloAINPlayers:
    """IA adaptada para N jugadores"""

    def __init__(self, difficulty='medium', num_players=3):
        self.difficulty = difficulty
        self.num_players = num_players

        # Tabla de pesos posicionales
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

    def choose_move(self, valid_moves, board, player_number):
        if not valid_moves:
            return None

        if self.difficulty == 'easy':
            return random.choice(valid_moves)
        elif self.difficulty == 'medium':
            return self.greedy_move(valid_moves, board, player_number)
        else:
            return self.minimax_move(valid_moves, board, player_number)

    def greedy_move(self, valid_moves, board, player_number):
        """Estrategia codiciosa para N jugadores"""
        best_move = None
        best_score = -float('inf')

        for move in valid_moves:
            row, col = move
            temp_board = self.simulate_move(board, row, col, player_number)

            # Contar fichas ganadas
            pieces_gained = np.sum(temp_board == player_number) - np.sum(board == player_number)
            position_value = self.position_weights[row][col]

            # Bonus por reducir fichas del líder
            leader_penalty = self.calculate_leader_penalty(board, temp_board, player_number)

            score = pieces_gained * 10 + position_value + leader_penalty * 3

            if score > best_score:
                best_score = score
                best_move = move

        return best_move

    def minimax_move(self, valid_moves, board, player_number, depth=2):
        """Minimax adaptado para múltiples jugadores"""
        best_move = None
        best_score = -float('inf')

        for move in valid_moves:
            row, col = move
            temp_board = self.simulate_move(board, row, col, player_number)
            score = self.evaluate_board(temp_board, player_number)

            if score > best_score:
                best_score = score
                best_move = move

        return best_move

    def calculate_leader_penalty(self, old_board, new_board, player_number):
        """Penaliza al líder actual"""
        penalty = 0

        for p in range(1, self.num_players + 1):
            if p != player_number:
                old_count = np.sum(old_board == p)
                new_count = np.sum(new_board == p)

                if old_count > np.sum(old_board == player_number):
                    # Era el líder
                    penalty += (old_count - new_count) * 2

        return penalty

    def evaluate_board(self, board, player_number):
        """Evalúa el tablero para N jugadores"""
        my_pieces = np.sum(board == player_number)
        my_position_value = np.sum((board == player_number) * self.position_weights)

        # Comparar con todos los oponentes
        total_opponent_pieces = 0
        total_opponent_position = 0

        for p in range(1, self.num_players + 1):
            if p != player_number:
                total_opponent_pieces += np.sum(board == p)
                total_opponent_position += np.sum((board == p) * self.position_weights)

        # Ventaja sobre promedio de oponentes
        avg_opponent_pieces = total_opponent_pieces / (self.num_players - 1)

        score = (my_pieces - avg_opponent_pieces) * 2 + \
                (my_position_value - total_opponent_position / (self.num_players - 1))

        return score

    def simulate_move(self, board, row, col, player):
        """Simula un movimiento"""
        new_board = copy.deepcopy(board)
        new_board[row][col] = player

        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                      (0, 1), (1, -1), (1, 0), (1, 1)]

        for dr, dc in directions:
            if self.check_direction(new_board, row, col, dr, dc, player):
                self.flip_pieces(new_board, row, col, dr, dc, player)

        return new_board

    def check_direction(self, board, row, col, dr, dc, player):
        r, c = row + dr, col + dc
        found_opponent = False

        while 0 <= r < 8 and 0 <= c < 8:
            cell = board[r][c]
            if cell == 0:
                return False
            elif cell != player:
                found_opponent = True
            elif cell == player:
                return found_opponent
            r += dr
            c += dc
        return False

    def flip_pieces(self, board, row, col, dr, dc, player):
        pieces_to_flip = []
        r, c = row + dr, col + dc

        while 0 <= r < 8 and 0 <= c < 8:
            cell = board[r][c]
            if cell == 0:
                break
            elif cell != player:
                pieces_to_flip.append((r, c))
            elif cell == player:
                for fr, fc in pieces_to_flip:
                    board[fr][fc] = player
                break
            r += dr
            c += dc


class AIGameClientNPlayers:
    def __init__(self, host='localhost', port=5555, difficulty='medium', think_time=1.5):
        self.host = host
        self.port = port
        self.socket = None
        self.player_number = None
        self.num_players = None
        self.game_state = None
        self.connected = False
        self.connection_status = "Desconectado"
        self.waiting_for_opponent = True
        self.difficulty_name = difficulty.upper()
        self.think_time = think_time
        self.next_move_time = None

        # IA (se inicializará cuando sepamos num_players)
        self.ai = None
        self.difficulty = difficulty

        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(f"IA {self.difficulty_name} - Othello N Jugadores")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 22)
        self.small_font = pygame.font.SysFont('Arial', 16)
        self.big_font = pygame.font.SysFont('Arial', 32, bold=True)

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(0.5)
            self.connected = True
            self.connection_status = "Conectado"
            print("✅ Conectado!")

            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            return True
        except Exception as e:
            self.connection_status = f"Error: {e}"
            print(f"❌ {e}")
            return False

    def receive_messages(self):
        buffer = ""
        while self.connected:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    self.connected = False
                    break

                buffer += data
                while '\n' in buffer:
                    message_str, buffer = buffer.split('\n', 1)
                    if message_str.strip():
                        try:
                            message = json.loads(message_str)
                            self.handle_message(message)
                        except json.JSONDecodeError:
                            pass
            except socket.timeout:
                continue
            except:
                self.connected = False
                break

    def handle_message(self, message):
        msg_type = message.get('type')

        if msg_type == 'welcome':
            self.player_number = message['player_number']
            self.num_players = message['num_players']

            # Inicializar IA ahora que sabemos num_players
            self.ai = OthelloAINPlayers(self.difficulty, self.num_players)

            player_name = PLAYER_NAMES[self.player_number - 1] if self.player_number <= len(PLAYER_NAMES) else f"J{self.player_number}"
            self.connection_status = f"IA {player_name} - {self.difficulty_name}"
            print(f"🎯 Soy {player_name}")

        elif msg_type == 'waiting':
            self.waiting_for_opponent = True

        elif msg_type == 'game_start':
            self.game_state = message['game_state']
            self.num_players = self.game_state['num_players']
            self.waiting_for_opponent = False
            print("🎮 ¡Juego iniciado!")
            self.schedule_next_move()

        elif msg_type == 'game_update':
            self.game_state = message['game_state']
            self.waiting_for_opponent = False
            self.schedule_next_move()

    def schedule_next_move(self):
        if (self.game_state and
                not self.game_state['game_over'] and
                self.game_state['current_player'] == self.player_number):
            self.next_move_time = time.time() + self.think_time

    def check_and_make_move(self):
        if self.next_move_time and time.time() >= self.next_move_time:
            self.next_move_time = None
            self.make_ai_move()

    def make_ai_move(self):
        if not self.game_state or self.game_state['game_over']:
            return
        if self.game_state['current_player'] != self.player_number:
            return

        valid_moves = self.game_state.get('valid_moves', [])
        if not valid_moves:
            return

        print(f"🤔 Pensando... ({len(valid_moves)} opciones)")

        board = np.array(self.game_state['board'])
        move = self.ai.choose_move(valid_moves, board, self.player_number)

        if move:
            row, col = move
            print(f"🎯 Jugando en ({row}, {col})")
            self.send_move(row, col)

    def send_move(self, row, col):
        message = {'type': 'move', 'row': row, 'col': col}
        try:
            message_str = json.dumps(message) + '\n'
            self.socket.send(message_str.encode('utf-8'))
        except:
            pass

    def draw_waiting_screen(self):
        self.screen.fill(BACKGROUND)

        for i in range(BOARD_SIZE + 1):
            pygame.draw.line(self.screen, BLACK, (0, i * CELL_SIZE), (800, i * CELL_SIZE), 2)
            pygame.draw.line(self.screen, BLACK, (i * CELL_SIZE, 0), (i * CELL_SIZE, 800), 2)

        overlay = pygame.Surface((WIDTH, 800), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        title = self.big_font.render(f"IA {self.difficulty_name}", True, YELLOW)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 250))

        if self.player_number:
            color = PLAYER_COLORS[self.player_number - 1]
            name = PLAYER_NAMES[self.player_number - 1] if self.player_number <= len(PLAYER_NAMES) else f"Jugador {self.player_number}"
            text = f"Soy: {name}"
            surface = self.font.render(text, True, color)
            self.screen.blit(surface, (WIDTH // 2 - surface.get_width() // 2, 320))

        if self.waiting_for_opponent:
            wait = self.big_font.render("ESPERANDO...", True, WHITE)
            self.screen.blit(wait, (WIDTH // 2 - wait.get_width() // 2, 400))

    def draw_board(self):
        if not self.game_state:
            return

        self.screen.fill(BACKGROUND)

        for i in range(BOARD_SIZE + 1):
            pygame.draw.line(self.screen, BLACK, (0, i * CELL_SIZE), (800, i * CELL_SIZE), 2)
            pygame.draw.line(self.screen, BLACK, (i * CELL_SIZE, 0), (i * CELL_SIZE, 800), 2)

        board = self.game_state['board']
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if board[row][col] != 0:
                    player = board[row][col]
                    center_x = col * CELL_SIZE + CELL_SIZE // 2
                    center_y = row * CELL_SIZE + CELL_SIZE // 2
                    color = PLAYER_COLORS[player - 1]
                    pygame.draw.circle(self.screen, color, (center_x, center_y), DOT_RADIUS)
                    pygame.draw.circle(self.screen, (100, 100, 100), (center_x, center_y), DOT_RADIUS, 2)

        self.draw_game_info()

    def draw_game_info(self):
        if not self.game_state:
            return

        panel_y = 800
        pygame.draw.rect(self.screen, BLACK, (0, panel_y, WIDTH, 50))

        current = self.game_state['current_player']
        current_name = PLAYER_NAMES[current - 1] if current <= len(PLAYER_NAMES) else f"J{current}"

        if self.game_state['game_over']:
            turn_text = "TERMINADO"
            turn_color = RED
        else:
            is_my_turn = current == self.player_number
            turn_text = f"Turno: {current_name}" + (" (YO)" if is_my_turn else "")
            turn_color = GREEN if is_my_turn else WHITE

        turn_surface = self.font.render(turn_text, True, turn_color)
        self.screen.blit(turn_surface, (10, panel_y + 15))

        scores = self.game_state['scores']
        x_pos = 350
        for i in range(1, self.num_players + 1):
            score = scores.get(f'player_{i}', 0)
            color = PLAYER_COLORS[i - 1]

            pygame.draw.circle(self.screen, color, (x_pos, panel_y + 25), 12)
            pygame.draw.circle(self.screen, WHITE, (x_pos, panel_y + 25), 12, 1)

            score_surface = self.small_font.render(f"{score}", True, WHITE)
            self.screen.blit(score_surface, (x_pos + 20, panel_y + 16))

            x_pos += 80

        if self.game_state['game_over']:
            self.draw_winner_screen()

    def draw_winner_screen(self):
        overlay = pygame.Surface((WIDTH, 800), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        scores = self.game_state['scores']
        max_score = max(scores.values())
        winners = [int(k.split('_')[1]) for k, v in scores.items() if v == max_score]

        if len(winners) == 1:
            winner = winners[0]
            name = PLAYER_NAMES[winner - 1] if winner <= len(PLAYER_NAMES) else f"J{winner}"
            title_text = f"¡GANA {name.upper()}!"
            title_color = PLAYER_COLORS[winner - 1]
        else:
            title_text = "¡EMPATE!"
            title_color = YELLOW

        title_surface = self.big_font.render(title_text, True, title_color)
        title_rect = title_surface.get_rect(center=(WIDTH // 2, 250))

        bg_rect = pygame.Rect(title_rect.x - 20, title_rect.y - 10,
                              title_rect.width + 40, title_rect.height + 20)
        pygame.draw.rect(self.screen, BLACK, bg_rect)
        pygame.draw.rect(self.screen, title_color, bg_rect, 3)
        self.screen.blit(title_surface, title_rect)

        y = 350
        for i in range(1, self.num_players + 1):
            score = scores.get(f'player_{i}', 0)
            color = PLAYER_COLORS[i - 1]
            name = PLAYER_NAMES[i - 1] if i <= len(PLAYER_NAMES) else f"Jugador {i}"

            pygame.draw.circle(self.screen, color, (WIDTH // 2 - 100, y), 15)
            text = f"{name}: {score}"
            if i in winners:
                text += " 🏆"
            surface = self.font.render(text, True, WHITE)
            self.screen.blit(surface, (WIDTH // 2 - 60, y - 10))
            y += 40

    def run(self):
        if not self.connect():
            print("⚠️ No conectado")

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            self.check_and_make_move()

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
    print("🤖 IA OTHELLO N-JUGADORES")
    print("="*50)

    host = input("Servidor [localhost]: ").strip() or 'localhost'
    port_input = input("Puerto [5555]: ").strip()
    port = int(port_input) if port_input.isdigit() else 5555

    print("\nDificultad:")
    print("1. Fácil")
    print("2. Medio")
    print("3. Difícil")

    diff_input = input("Selecciona [2]: ").strip()
    difficulty_map = {'1': 'easy', '2': 'medium', '3': 'hard', '': 'medium'}
    difficulty = difficulty_map.get(diff_input, 'medium')

    print(f"\n🚀 Iniciando IA {difficulty.upper()}...")
    client = AIGameClientNPlayers(host, port, difficulty, think_time=1.5)
    client.run()