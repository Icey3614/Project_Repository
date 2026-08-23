"""贪吃蛇核心逻辑（与界面无关，便于单元测试）。

        支持两种模式：
          - single：单条蛇
          - duel：双人竞技，两条蛇同场；
            蛇头撞到对方身体的一方判负，蛇头相撞时比较双方积分，积分低者判负，
            积分相同则双方判负（平局）。

        食物机制：开局随机生成若干个豆子，之后由界面层定时调用 spawn_one_food()
        持续补充——豆子数量没有固定上限，不吃也会不断随机出现（直到棋盘被占满）。
"""
from __future__ import annotations

import random
from collections import deque
from typing import Optional

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)


class Snake:
    """一条蛇：身体、方向、方向输入缓冲与积分。"""

    def __init__(
        self,
        cells: list[tuple[int, int]],
        direction: tuple[int, int],
    ) -> None:
        self.cells: deque[tuple[int, int]] = deque(cells)
        self.direction = direction
        self.pending: deque[tuple[int, int]] = deque()
        self.eaten = 0
        self.alive = True

    @property
    def head(self) -> tuple[int, int]:
        return self.cells[0]

    @property
    def length(self) -> int:
        return len(self.cells)

    def set_direction(self, direction: tuple[int, int]) -> None:
        """请求一个转向（进入缓冲，下一步生效）。

        判定是否掉头时，与“当前方向或缓冲中最后一个方向”比较，
        从而支持 先上后左 这类快速连续转向。
        """
        last = self.pending[-1] if self.pending else self.direction
        if direction == last:
            return
        if direction == (-last[0], -last[1]):
            return
        if len(self.pending) >= 4:
            return
        self.pending.append(direction)

    def consume_direction(self) -> None:
        """从缓冲里取下一个合法方向。"""
        while self.pending:
            direction = self.pending.popleft()
            if direction == self.direction:
                continue
            if direction == (-self.direction[0], -self.direction[1]):
                continue
            self.direction = direction
            return


class SnakeGame:
    """一局贪吃蛇的状态与规则。"""

    def __init__(
        self,
        width: int,
        height: int,
        wrap: bool = False,
        mode: str = "single",
        initial_food_count: int = 3,
    ) -> None:
        self.width = width
        self.height = height
        self.wrap = wrap
        self.mode = mode
        self.initial_food_count = max(1, initial_food_count)
        self.reset()

    def reset(self) -> None:
        cy = self.height // 2
        if self.mode == "duel":
            self.snakes: list[Snake] = [
                Snake([(4, cy), (3, cy), (2, cy)], RIGHT),
                Snake(
                    [
                        (self.width - 5, cy),
                        (self.width - 4, cy),
                        (self.width - 3, cy),
                    ],
                    LEFT,
                ),
            ]
        else:
            cx = self.width // 2
            self.snakes = [Snake([(cx, cy), (cx - 1, cy), (cx - 2, cy)], RIGHT)]
        self.foods: set[tuple[int, int]] = set()
        for _ in range(self.initial_food_count):
            self.spawn_one_food()

    # ---------- 输入 ----------
    def set_direction(self, player: int, direction: tuple[int, int]) -> None:
        """玩家 0=WASD（单人也用它），玩家 1=方向键（仅双人）。"""
        if 0 <= player < len(self.snakes) and self.snakes[player].alive:
            self.snakes[player].set_direction(direction)

    # ---------- 移动与食物 ----------
    def next_head(self, snake: Snake) -> tuple[int, int]:
        hx, hy = snake.head
        dx, dy = snake.direction
        nx, ny = hx + dx, hy + dy
        if self.wrap:
            nx %= self.width
            ny %= self.height
        return nx, ny

    def free_cells(self) -> list[tuple[int, int]]:
        occupied = set(self.foods)
        for snake in self.snakes:
            occupied.update(snake.cells)
        return [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if (x, y) not in occupied
        ]

    def spawn_one_food(self) -> bool:
        """在场地上随机生成一个豆子；没有空位时返回 False。"""
        free = self.free_cells()
        if not free:
            return False
        self.foods.add(random.choice(free))
        return True

    def step(self) -> None:
        """同步推进一格：转向、移动、吃食物、碰撞判定。"""
        # 1. 计算每条存活蛇的下一格与是否吃到食物
        moves: list[tuple[Snake, tuple[int, int], bool]] = []
        for snake in self.snakes:
            if not snake.alive:
                continue
            snake.consume_direction()
            head = self.next_head(snake)
            moves.append((snake, head, head in self.foods))
        will_eat = {snake: eat for snake, _, eat in moves}

        # 3. 碰撞判定（经典规则：撞到自己/对方身体判负；不吃时尾巴那一格不算）
        deaths: set[Snake] = set()
        for snake, head, _ in moves:
            if not self.wrap and not (
                0 <= head[0] < self.width and 0 <= head[1] < self.height
            ):
                deaths.add(snake)
                continue
            own_body = set(snake.cells)
            if not will_eat[snake]:
                own_body.discard(snake.cells[-1])
            if head in own_body:
                deaths.add(snake)
                continue
            for other, other_head, _ in moves:
                if other is snake:
                    continue
                if head == other_head:
                    # 蛇头相撞：比较积分
                    if snake.eaten == other.eaten:
                        deaths.update((snake, other))
                    elif snake.eaten < other.eaten:
                        deaths.add(snake)
                    else:
                        deaths.add(other)
                    continue
                other_body = set(other.cells)
                if not will_eat[other]:
                    other_body.discard(other.cells[-1])
                if head in other_body:
                    deaths.add(snake)

        # 4. 应用移动
        for snake, head, will_eat in moves:
            if snake in deaths:
                snake.alive = False
                continue
            snake.cells.appendleft(head)
            if will_eat:
                snake.eaten += 1
                self.foods.discard(head)
            else:
                snake.cells.pop()

    # ---------- 速度与胜负 ----------
    def effective_speed(self, player: int, base_speed: int, speed_up: bool) -> int:
        snake = self.snakes[min(player, len(self.snakes) - 1)]
        if not speed_up:
            return base_speed
        return min(base_speed * 2, int(base_speed * (1 + 0.08 * snake.eaten)) or 1)

    def status(self) -> tuple[str, Optional[str]]:
        """返回 (是否结束, 结果)。结果：None 单人结束 / p1 / p2 / draw。"""
        if self.mode == "single":
            if not self.snakes[0].alive:
                return "over", None
            return "running", None
        alive = [snake for snake in self.snakes if snake.alive]
        if not alive:
            return "over", "draw"
        if len(alive) == 1:
            return "over", "p1" if alive[0] is self.snakes[0] else "p2"
        return "running", None

    def end_by_timer(self) -> str:
        """倒计时结束时比较双方积分。"""
        if self.snakes[0].eaten == self.snakes[1].eaten:
            return "draw"
        return "p1" if self.snakes[0].eaten > self.snakes[1].eaten else "p2"
