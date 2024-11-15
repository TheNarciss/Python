import serial  # Pour gérer la communication série
import pygame
import sys
import time
import random
import csv
import os

# Configuration de la connexion série
SERIAL_PORT = '/dev/cu.wchusbserial1130'  # Remplacez par le port correspondant sur votre système
BAUD_RATE = 9600

# Initialisation de la connexion série
try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
except Exception as e:
    print(f"Erreur de connexion avec l'Arduino : {e}")
    arduino = None

# Initialisation de Pygame
pygame.init()

# Dimensions de l'écran
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Jeu de Réaction")

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (50, 150, 255)
RED = (255, 0, 0)
GRAY = (200, 200, 200)
GREEN = (0, 255, 0)

# Police
FONT = pygame.font.Font(None, 36)

# Chemin vers le fichier CSV
CSV_FILE = '/Users/clementgardair/Documents/GitHub/PythonWorkShop/Base.csv'

# Initialisation du fichier CSV si inexistant
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        header = ['player_name'] + [chr(letter) for letter in range(65, 91)] + ['avg_time']  # A à Z + avg_time
        writer.writerow(header)

# Classe pour le menu principal (inchangée)
class Menu:
    def __init__(self):
        self.player_name = ""
        self.letters_to_play = ""
        self.active_field = None  # None, "name", or "letters"
        self.blink_timer = time.time()
        self.blink_state = True  # True: affiché, False: caché

    def draw_input_box(self, label, x, y, width, height, active, text):
        color = BLUE if active else GRAY
        pygame.draw.rect(screen, color, (x, y, width, height), 2)
        input_text = FONT.render(text, True, BLACK)
        screen.blit(input_text, (x + 10, y + height // 4))

        if active and self.blink_state:
            blink_x = x + 10 + input_text.get_width()
            pygame.draw.line(screen, BLACK, (blink_x, y + 10), (blink_x, y + height - 10), 2)

        label_text = FONT.render(label, True, BLACK)
        screen.blit(label_text, (x, y - 30))

    def draw_button(self, label, x, y, width, height, hover):
        color = GREEN if hover else GRAY
        pygame.draw.rect(screen, color, (x, y, width, height))
        button_text = FONT.render(label, True, WHITE)
        text_rect = button_text.get_rect(center=(x + width // 2, y + height // 2))
        screen.blit(button_text, text_rect)

    def display_menu(self):
        screen.fill(WHITE)
        if time.time() - self.blink_timer > 0.5:
            self.blink_state = not self.blink_state
            self.blink_timer = time.time()

        self.draw_input_box("Nom du joueur", 100, 150, 600, 50, self.active_field == "name", self.player_name)
        self.draw_input_box("Lettres à jouer", 100, 250, 600, 50, self.active_field == "letters", self.letters_to_play)

        mouse_x, mouse_y = pygame.mouse.get_pos()
        hover_score = 100 <= mouse_x <= 350 and 350 <= mouse_y <= 400
        hover_start = 450 <= mouse_x <= 700 and 350 <= mouse_y <= 400

        self.draw_button("Scores", 100, 350, 250, 50, hover_score)
        self.draw_button("Start", 450, 350, 250, 50, hover_start)

        pygame.display.flip()

        return hover_score, hover_start

    def main_menu(self):
        running = True
        while running:
            hover_score, hover_start = self.display_menu()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if 100 <= event.pos[0] <= 700 and 150 <= event.pos[1] <= 200:
                        self.active_field = "name"
                    elif 100 <= event.pos[0] <= 700 and 250 <= event.pos[1] <= 300:
                        self.active_field = "letters"
                    elif hover_score:
                        self.show_scores()
                    elif hover_start and self.player_name and self.letters_to_play:
                        game = Game(self.player_name, self.letters_to_play)
                        game.run_game()
                        running = False

                elif event.type == pygame.KEYDOWN:
                    if self.active_field == "name":
                        if event.key == pygame.K_BACKSPACE:
                            self.player_name = self.player_name[:-1]
                        elif len(self.player_name) < 20:
                            self.player_name += event.unicode
                    elif self.active_field == "letters":
                        if event.key == pygame.K_BACKSPACE:
                            self.letters_to_play = self.letters_to_play[:-1]
                        elif len(self.letters_to_play) < 26 and event.unicode.isalpha():
                            self.letters_to_play += event.unicode.upper()

    def show_scores(self):
        screen.fill(WHITE)
        y_offset = 100
        try:
            with open(CSV_FILE, mode='r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    score_text = FONT.render(
                        f"{row['player_name']} : {row['avg_time']}s",
                        True,
                        BLACK,
                    )
                    screen.blit(score_text, (50, y_offset))
                    y_offset += 40
        except Exception as e:
            error_text = FONT.render(f"Erreur : {e}", True, RED)
            screen.blit(error_text, (50, y_offset))
        pygame.display.flip()

        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    waiting = False

# Classe pour gérer le jeu (avec gestion de la pause)
class Game:
    def save_results_to_csv(self):
        # Calcul des moyennes pour chaque lettre (A à Z)
        avg_times_per_letter = {}
        for letter in self.reaction_times:
            avg_times_per_letter[letter] = sum(self.reaction_times[letter]) / len(self.reaction_times[letter])

        # Calcul de la moyenne générale (temps moyen pour toutes les lettres)
        all_times = [time for times in self.reaction_times.values() for time in times]
        avg_time = sum(all_times) / len(all_times) if all_times else 0

        # Préparer la ligne à ajouter dans le fichier CSV
        row = [self.player_name]  # Nom du joueur
        for letter in range(65, 91):  # Pour chaque lettre de A à Z (ASCII 65 à 90)
            letter_char = chr(letter)
            # Si des temps sont enregistrés pour la lettre, on ajoute la moyenne, sinon 0
            letter_avg_time = avg_times_per_letter.get(letter_char, 0)
            row.append(letter_avg_time)
        row.append(avg_time)  # Temps moyen général

        # Enregistrement des résultats dans le fichier CSV
        try:
            with open(CSV_FILE, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(row)
        except Exception as e:
            print(f"Erreur lors de l'enregistrement des résultats dans le CSV : {e}")

    def __init__(self, player_name, letters):
        self.player_name = player_name
        self.letters = list(letters)
        self.reaction_times = {}
        self.paused = False

    def draw_button(self, label, x, y, width, height, hover):
        # Dessiner un bouton avec une couleur différente si la souris est au-dessus
        color = GREEN if hover else GRAY
        pygame.draw.rect(screen, color, (x, y, width, height))
        button_text = FONT.render(label, True, WHITE)
        text_rect = button_text.get_rect(center=(x + width // 2, y + height // 2))
        screen.blit(button_text, text_rect)

    def draw_pause_menu(self):
        # Dessiner le menu de pause
        screen.fill(WHITE)
        pause_text = FONT.render("Jeu en Pause", True, BLACK)
        screen.blit(pause_text, (SCREEN_WIDTH // 2 - pause_text.get_width() // 2, 100))

        mouse_x, mouse_y = pygame.mouse.get_pos()

        hover_resume = 250 <= mouse_x <= 550 and 200 <= mouse_y <= 270
        hover_menu = 250 <= mouse_x <= 550 and 300 <= mouse_y <= 370

        self.draw_button("Reprendre", 250, 200, 300, 70, hover_resume)
        self.draw_button("Menu Principal", 250, 300, 300, 70, hover_menu)

        pygame.display.flip()

        return hover_resume, hover_menu
    

    def handle_pause(self):
        # Gérer les actions du menu de pause
        while self.paused:
            hover_resume, hover_menu = self.draw_pause_menu()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if hover_resume:
                        self.paused = False  # Reprendre le jeu
                    elif hover_menu:
                        self.save_results_to_csv()
                        return True  # Retour au menu principal

        return False  # Retourner à la partie en cours

    def run_game(self):
        # Démarrer le jeu et gérer la logique de jeu
        clock = pygame.time.Clock()
        running = True
        current_letter = None
        start_time = None

        while running:
            screen.fill(WHITE)
            
            # Vérifier si l'Arduino a envoyé un signal de pause
            if arduino and arduino.in_waiting > 0:
                button_state = arduino.readline().decode().strip()
                print(f"Signal Arduino reçu : {button_state}")  # Affiche le signal reçu
                if button_state == "PAUSE":
                    self.paused = True
                    if self.handle_pause():  # Si on appuie sur "Menu Principal"
                        menu.main_menu() # Quitter le jeu et revenir au menu principal
                        break

            pygame.draw.rect(screen, BLACK, (SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT // 2 - 50, 100, 100))

            if not current_letter:
                current_letter = random.choice(self.letters)
                start_time = time.time()

            font = pygame.font.Font(None, 74)
            letter_surface = font.render(current_letter, True, WHITE)
            letter_rect = letter_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(letter_surface, letter_rect)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.unicode.upper() == current_letter:
                        reaction_time = time.time() - start_time
                        if current_letter in self.reaction_times:
                            self.reaction_times[current_letter].append(reaction_time)
                        else:
                            self.reaction_times[current_letter] = [reaction_time]
                        current_letter = None

            if self.reaction_times:
                avg_time = sum([sum(times) for times in self.reaction_times.values()]) / sum(
                    [len(times) for times in self.reaction_times.values()]
                )
                avg_text = FONT.render(f"Temps moyen : {avg_time:.2f}s", True, BLACK)
                screen.blit(avg_text, (20, 20))

            pygame.display.flip()
            clock.tick(60)

        self.save_results_to_csv()    
        
# Lancement du menu
menu = Menu()
menu.main_menu()
