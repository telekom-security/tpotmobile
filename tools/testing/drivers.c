#include <SDL.h>
#include <stdio.h>

int main(void) {
    int i, num_drivers;
    const char *driver_name;

    SDL_Init(SDL_INIT_VIDEO);

    num_drivers = SDL_GetNumVideoDrivers();
    printf("Available SDL Video Drivers:\n");
    for (i = 0; i < num_drivers; i++) {
        driver_name = SDL_GetVideoDriver(i);
        printf("%d: %s\n", i, driver_name);
    }

    SDL_Quit();
    return 0;
}
