import pygame
from copy import deepcopy
from random import choice, randrange

W, H = 10, 20
TILE = 45
GAME_RES = W * TILE, H * TILE
RES = 750, 940
FPS = 60

figures_pos = [[(-1, 0), (-2, 0), (0, 0), (1, 0)],
                   [(0, -1), (-1, -1), (-1, 0), (0, 0)],
                   [(-1, 0), (-1, 1), (0, 0), (0, -1)],
                   [(0, 0), (-1, 0), (0, 1), (-1, -1)],
                   [(0, 0), (0, -1), (0, 1), (-1, -1)],
                   [(0, 0), (0, -1), (0, 1), (1, -1)],
                   [(0, 0), (0, -1), (0, 1), (-1, 0)]]

pygame.init()
main_font = pygame.font.Font('font/font.ttf', 65)
font = pygame.font.Font('font/font.ttf', 45)
figures = [[pygame.Rect(x + W // 2, y + 1, 1, 1) for x, y in fig_pos] for fig_pos in figures_pos]
title_tetris = main_font.render('TETRIS', True, pygame.Color('darkorange'))
title_score = font.render('score:', True, pygame.Color('green'))
scores = {0: 0, 1: 100, 2: 300, 3: 700, 4: 1500}
grid = [pygame.Rect(x * TILE, y * TILE, TILE, TILE) for x in range(W) for y in range(H)]
get_color = lambda : (randrange(30, 256), randrange(30, 256), randrange(30, 256))
grid = [pygame.Rect(x * TILE, y * TILE, TILE, TILE) for x in range(W) for y in range(H)]

class PyTetris:
    def __init__(self):
        self.sc = pygame.display.set_mode(RES)
        self.game_sc = pygame.Surface(GAME_RES)
        self.clock = pygame.time.Clock()
        self.figures_rect = pygame.Rect(0, 0, TILE - 2, TILE - 2)
        self.field = [[0 for i in range(W)] for j in range(H)]
        self.anim_count, self.anim_speed, self.anim_limit = 0, 60, 2000
        self.figures, self.next_figures = deepcopy(choice(figures)), deepcopy(choice(figures))
        self.color, self.next_color = get_color(), get_color()
        self.score, self.lines = 0, 0
        self.game_over = False

    def check_borders(self, i):
        if self.figures[i].x < 0 or self.figures[i].x > W - 1:
            return False
        elif self.figures[i].y > H - 1 or self.field[self.figures[i].y][self.figures[i].x]:
            return False
        return True

    def play_step(self):
            dx, rotate = 0, False
            self.sc.fill((0, 0, 0))
            self.sc.blit(self.game_sc, (20, 20))
            self.game_sc.fill((100, 100, 100))
            # delay for full self.lines
            for i in range(self.lines):
                pygame.time.wait(200)
            # control
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        dx = -1
                    elif event.key == pygame.K_RIGHT:
                        dx = 1
                    elif event.key == pygame.K_DOWN:
                        self.anim_limit = 0
                    elif event.key == pygame.K_UP:
                        rotate = True

            # move x
            self.figures_old = deepcopy(self.figures)
            for i in range(4):
                self.figures[i].x += dx
                if not self.check_borders(i):
                    self.figures = deepcopy(self.figures_old)
                    break

            # move y
            self.anim_count += self.anim_speed
            if self.anim_count > self.anim_limit:
                self.anim_count = 0
                self.figures_old = deepcopy(self.figures)
                for i in range(4):
                    self.figures[i].y += 1
                    if not self.check_borders(i):
                        for i in range(4):
                            self.field[self.figures_old[i].y][self.figures_old[i].x] = self.color
                        self.figures, self.color = self.next_figures, self.next_color
                        self.next_figures, self.next_color = deepcopy(choice(figures)), get_color()
                        self.anim_limit = 2000
                        break

            # rotate
            center = self.figures[0]
            self.figures_old = deepcopy(self.figures)
            if rotate:
                for i in range(4):
                    x = self.figures[i].y - center.y
                    y = self.figures[i].x - center.x
                    self.figures[i].x = center.x - x
                    self.figures[i].y = center.y + y
                    if not self.check_borders(i):
                        self.figures = deepcopy(self.figures_old)
                        break

            # check self.lines
            line, self.lines = H - 1, 0
            for row in range(H - 1, -1, -1):
                count = 0
                for i in range(W):
                    if self.field[row][i]:
                        count += 1
                    self.field[line][i] = self.field[row][i]
                if count < W:
                    line -= 1
                else:
                    self.anim_speed += 3
                    self.lines += 1
            # compute self.score
            self.score += scores[self.lines]
            # draw grid
            [pygame.draw.rect(self.game_sc, (40, 40, 40), i_rect, 1) for i_rect in grid]
            # draw figure
            for i in range(4):
                self.figures_rect.x = self.figures[i].x * TILE
                self.figures_rect.y = self.figures[i].y * TILE
                pygame.draw.rect(self.game_sc, self.color, self.figures_rect)
            # draw self.field
            for y, raw in enumerate(self.field):
                for x, col in enumerate(raw):
                    if col:
                        self.figures_rect.x, self.figures_rect.y = x * TILE, y * TILE
                        pygame.draw.rect(self.game_sc, col, self.figures_rect)
            # draw next figure
            for i in range(4):
                self.figures_rect.x = self.next_figures[i].x * TILE + 380
                self.figures_rect.y = self.next_figures[i].y * TILE + 185
                pygame.draw.rect(self.sc, self.next_color, self.figures_rect)
            # draw titles
            self.sc.blit(title_tetris, (485, -10))
            self.sc.blit(title_score, (535, 780))
            self.sc.blit(font.render(str(self.score), True, pygame.Color('white')), (550, 840))

            # check for game over
            for i in range(W):
                if self.field[0][i]:
                    self.game_over = True

            pygame.display.flip()
            self.clock.tick(FPS)


if __name__ == "__main__":
    tetris = PyTetris()

    while not tetris.game_over:
      tetris.play_step()
