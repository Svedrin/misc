
import sys

import pygame
import pygame.camera
import pygame.display
import pygame.draw
import pygame.font
import pygame.image

from PIL import Image, ImageEnhance, ImageDraw
from time import sleep

pygame.init()

pygame.camera.init()
cam = pygame.camera.Camera("/dev/video1", (1920, 1080) )
cam.start()

pygame.display.init()
screen = pygame.display.set_mode((1920, 1080))
font = pygame.font.Font(None, 60)

while True:
    surface_img = cam.get_image()
    screen.fill((0, 0, 0, 255))
    screen.blit(surface_img, (0, 0))

    pygame.draw.line(
        screen, (255, 0, 0, 255),
        (1920/2 - 50, 1080/2),
        (1920/2 + 50, 1080/2),
        1)
    pygame.draw.line(
        screen, (255, 0, 0, 255),
        (1920/2, 1080/2 - 50),
        (1920/2, 1080/2 + 50),
        1)

    pil_string_image = pygame.image.tostring(surface_img, "RGBA", False)
    im = Image.frombytes("RGBA", (1920, 1080), pil_string_image)

    sw = im.convert("LA")

    contrast = ImageEnhance.Contrast(sw)

    sw = contrast.enhance(5)

    #draw = ImageDraw.Draw(sw)

    thresh = 150
    min_x = None
    max_x = None
    min_y = None
    max_y = None

    for x in range( 1920 / 2 - 500, 1920 / 2 + 500, 10 ):
        px, alpha = sw.getpixel((x, 1080/2))
        if min_x is None:
            if px <= thresh:
                min_x = x
        else:
            if max_x is None:
                if px > thresh:
                    max_x = x

    for y in range( 1080 / 2 - 500, 1080 / 2 + 500, 10 ):
        px, alpha = sw.getpixel((1920/2, y))
        if min_y is None:
            if px <= thresh:
                min_y = y
        else:
            if max_y is None:
                if px > thresh:
                    max_y = y

    #print min_x, min_y, max_x, max_y

    if min_x and min_y and max_x and max_y:
        pygame.draw.lines(
            screen, (0, 0, 255, 255), True,
            ((min_x, min_y),
             (min_x, max_y),
             (max_x, max_y),
             (max_x, min_y)),
            2)

        dark_pixels = 0

        for x in range(min_x, max_x):
            for y in range(min_y, max_y):
                px, alpha = sw.getpixel((x, y))
                if px < thresh:
                    dark_pixels += 1

        prozentes = font.render(
            '%.2f%%' % (dark_pixels / ( (max_x - min_x) * float(max_y - min_y) ) * 100.),
            0, (0, 255, 0, 255), (0, 0, 0, 0)
        )
    else:
        prozentes = font.render(
            '??.??%',
            0, (0, 255, 0, 255), (0, 0, 0, 0)
        )
    screen.blit(prozentes, (10, 10))

    pygame.display.flip()
    sleep(0.001)
