import pygame
import random
from collections import deque

# 初始化Pygame
pygame.init()

# 设置游戏窗口大小
屏幕宽度 = 320
屏幕高度 = 480
格子大小 = 10  # 添加格子大小常量

# 窗口标题和初始设置
窗口标题 = "贪吃蛇"
窗口 = pygame.display.set_mode((屏幕宽度, 屏幕高度))
pygame.display.set_caption(窗口标题)

# 游戏颜色设置
背景色 = (0, 0, 0)
蛇色 = (0, 255, 0)
食物色 = (255, 0, 0)
墙壁色 = (100, 100, 100)

# 游戏参数设置
初始蛇长度 = 3
食物数目 = 5
食物生成频率 = 150
游戏速度 = 15

class 贪吃蛇:
    def __init__(self):
        self.serpientes = deque()  # 使用deque代替list提高性能
        self.foods = set()  # 使用set代替list提高查找性能
        self.score = 0
        self.direction = [1, 0]  # 初始向右移动
        self.surface = pygame.Surface((屏幕宽度, 屏幕高度))  # 创建缓存surface
        self.last_food_time = 0
        
        # 初始化蛇的位置
        x = (屏幕宽度 // 格子大小 // 2) * 格子大小
        y = (屏幕高度 // 格子大小 // 2) * 格子大小
        for i in range(初始蛇长度):
            self.serpientes.append((x - i * 格子大小, y))

    def update(self):
        # 更新蛇的位置
        head_x = (self.serpientes[0][0] + self.direction[0] * 格子大小) % 屏幕宽度
        head_y = (self.serpientes[0][1] + self.direction[1] * 格子大小) % 屏幕高度
        new_head = (head_x, head_y)
        
        # 检查自身碰撞
        if new_head in set(list(self.serpientes)[1:]):
            return False
            
        self.serpientes.appendleft(new_head)
        
        # 检查是否吃到食物
        if new_head in self.foods:
            self.score += 1
            self.foods.remove(new_head)
        else:
            self.serpientes.pop()
            
        return True

    def draw(self, surface):
        # 清空surface
        surface.fill(背景色)
        
        # 绘制蛇
        for segment in self.serpientes:
            pygame.draw.rect(surface, 蛇色, 
                           (segment[0], segment[1], 格子大小-1, 格子大小-1))
        
        # 绘制食物
        for food in self.foods:
            pygame.draw.rect(surface, 食物色, 
                           (food[0], food[1], 格子大小-1, 格子大小-1))

def main():
    snake_obj = 贪吃蛇()
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)
    running = True
    
    # 预渲染分数文本
    score_surface = pygame.Surface((100, 30))
    score_surface.set_colorkey(背景色)
    
    while running:
        # 处理事件
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT and snake_obj.direction[0] != 1:
                    snake_obj.direction = [-1, 0]
                elif event.key == pygame.K_RIGHT and snake_obj.direction[0] != -1:
                    snake_obj.direction = [1, 0]
                elif event.key == pygame.K_UP and snake_obj.direction[1] != 1:
                    snake_obj.direction = [0, -1]
                elif event.key == pygame.K_DOWN and snake_obj.direction[1] != -1:
                    snake_obj.direction = [0, 1]

        # 生成食物
        if len(snake_obj.foods) < 食物数目:
            x = random.randrange(0, 屏幕宽度, 格子大小)
            y = random.randrange(0, 屏幕高度, 格子大小)
            food_pos = (x, y)
            if food_pos not in snake_obj.foods and food_pos not in snake_obj.serpientes:
                snake_obj.foods.add(food_pos)

        # 更新游戏状态
        if not snake_obj.update():
            running = False
            break

        # 绘制游戏画面
        snake_obj.draw(窗口)
        
        # 更新分数显示
        score_surface.fill(背景色)
        score_text = font.render(f"得分：{snake_obj.score}", True, 蛇色)
        score_surface.blit(score_text, (0, 0))
        窗口.blit(score_surface, (10, 10))
        
        pygame.display.flip()
        clock.tick(游戏速度)

    pygame.quit()

if __name__ == "__main__":
    main()
