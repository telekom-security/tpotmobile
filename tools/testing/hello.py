import pygame
import sys

# Initialize Pygame
pygame.init()

# Set up the display
screen_width, screen_height = 800, 480
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Hello World App")

# Set up the font
font = pygame.font.Font(None, 36)

# Main loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Fill the screen with a color
    screen.fill((255, 255, 255))  # White background

    # Render the text
    text = font.render("Hello World", True, (0, 0, 0))  # Black text
    text_rect = text.get_rect(center=(screen_width/2, screen_height/2))

    # Blit the text
    screen.blit(text, text_rect)

    # Update the display
    pygame.display.flip()

# Quit Pygame
pygame.quit()
sys.exit()
