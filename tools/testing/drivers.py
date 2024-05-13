import pygame

def list_sdl_video_drivers():
    # Initialize Pygame
    pygame.init()

    # Get the list of available video drivers
    driver = pygame.display.get_driver()
    print(driver)

    # Quit Pygame
    pygame.quit()

if __name__ == "__main__":
    list_sdl_video_drivers()
