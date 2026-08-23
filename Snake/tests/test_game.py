"""贪吃蛇核心逻辑的单元测试（单人 + 双人竞技）。"""
from collections import deque
import unittest

from game import DOWN, LEFT, RIGHT, UP, SnakeGame


class SinglePlayerTests(unittest.TestCase):
    def test_initial_state(self):
        game = SnakeGame(10, 10)
        self.assertTrue(game.snakes[0].alive)
        self.assertEqual(game.snakes[0].length, 3)
        self.assertEqual(len(game.foods), 3)  # 开局即有多颗豆子

    def test_spawn_one_food_grows_without_eating(self):
        game = SnakeGame(10, 10)
        before = len(game.foods)
        self.assertTrue(game.spawn_one_food())
        self.assertEqual(len(game.foods), before + 1)

    def test_spawn_one_food_fails_when_board_full(self):
        game = SnakeGame(3, 3, initial_food_count=1)
        snake_cells = set(game.snakes[0].cells)
        game.foods = {
            (x, y)
            for y in range(3)
            for x in range(3)
            if (x, y) not in snake_cells
        }
        self.assertFalse(game.spawn_one_food())

    def test_step_does_not_refill_food(self):
        game = SnakeGame(10, 10, wrap=True, initial_food_count=1)
        snake = game.snakes[0]
        snake.cells = deque([(2, 2), (1, 2), (0, 2)])
        snake.direction = RIGHT
        game.foods = {(3, 2)}
        game.step()
        self.assertEqual(snake.eaten, 1)
        self.assertEqual(len(game.foods), 0)  # 吃掉的不会自动补满，由定时器补充

    def test_move_forward(self):
        game = SnakeGame(10, 10)
        head_x, head_y = game.snakes[0].head
        game.step()
        self.assertEqual(game.snakes[0].head, (head_x + 1, head_y))
        self.assertEqual(game.snakes[0].length, 3)

    def test_wall_collision_without_wrap(self):
        game = SnakeGame(5, 5, wrap=False)
        snake = game.snakes[0]
        snake.cells = deque([(0, 2), (1, 2), (2, 2)])
        snake.direction = LEFT
        game.step()
        self.assertFalse(snake.alive)
        self.assertEqual(game.status()[0], "over")

    def test_wrap_through_wall(self):
        game = SnakeGame(5, 5, wrap=True)
        snake = game.snakes[0]
        snake.cells = deque([(0, 2), (1, 2), (2, 2)])
        snake.direction = LEFT
        game.step()
        self.assertTrue(snake.alive)
        self.assertEqual(snake.head, (4, 2))

    def test_eat_food_grows(self):
        game = SnakeGame(10, 10, wrap=True)
        snake = game.snakes[0]
        snake.cells = deque([(2, 2), (1, 2), (0, 2)])
        snake.direction = RIGHT
        game.foods = {(3, 2)}
        length_before = snake.length
        game.step()
        self.assertEqual(snake.length, length_before + 1)
        self.assertEqual(snake.eaten, 1)

    def test_no_reverse(self):
        game = SnakeGame(10, 10)
        snake = game.snakes[0]
        snake.set_direction(LEFT)
        self.assertEqual(snake.direction, RIGHT)
        self.assertEqual(len(snake.pending), 0)

    def test_direction_applied_on_next_step(self):
        game = SnakeGame(10, 10)
        snake = game.snakes[0]
        snake.set_direction(UP)
        self.assertEqual(snake.direction, RIGHT)
        game.step()
        self.assertEqual(snake.direction, UP)

    def test_rapid_turns_are_queued(self):
        game = SnakeGame(10, 10)
        snake = game.snakes[0]
        snake.set_direction(UP)
        snake.set_direction(LEFT)
        game.step()
        self.assertEqual(snake.direction, UP)
        game.step()
        self.assertEqual(snake.direction, LEFT)

    def test_queued_reverse_rejected(self):
        game = SnakeGame(10, 10)
        snake = game.snakes[0]
        snake.set_direction(UP)
        snake.set_direction(DOWN)
        self.assertEqual(len(snake.pending), 1)
        game.step()
        self.assertEqual(snake.direction, UP)

    def test_self_collision(self):
        game = SnakeGame(10, 10, wrap=True)
        snake = game.snakes[0]
        snake.cells = deque([(5, 5), (4, 5), (3, 5), (3, 4), (4, 4), (5, 4), (5, 3)])
        snake.direction = UP
        game.step()
        self.assertFalse(snake.alive)

    def test_effective_speed_without_speedup(self):
        game = SnakeGame(10, 10)
        self.assertEqual(game.effective_speed(0, 8, False), 8)

    def test_effective_speed_with_speedup(self):
        game = SnakeGame(10, 10)
        game.snakes[0].eaten = 10
        self.assertGreater(game.effective_speed(0, 8, True), 8)

    def test_effective_speed_capped(self):
        game = SnakeGame(10, 10)
        game.snakes[0].eaten = 1000
        self.assertEqual(game.effective_speed(0, 8, True), 16)


class DuelTests(unittest.TestCase):
    def test_duel_initial_two_snakes(self):
        game = SnakeGame(20, 10, mode="duel", initial_food_count=5)
        self.assertEqual(len(game.snakes), 2)
        self.assertEqual(len(game.foods), 5)
        self.assertNotEqual(game.snakes[0].head, game.snakes[1].head)

    def test_duel_head_hits_body_loses(self):
        game = SnakeGame(10, 10, wrap=False, mode="duel", initial_food_count=3)
        a, b = game.snakes
        a.cells = deque([(4, 5), (3, 5), (2, 5)])
        a.direction = RIGHT
        a.pending.clear()
        b.cells = deque([(6, 5), (5, 5), (4, 5)])
        b.direction = DOWN
        b.pending.clear()
        game.foods = set()
        game.step()
        self.assertFalse(a.alive)  # 撞到对方身体
        self.assertTrue(b.alive)
        self.assertEqual(game.status()[1], "p2")

    def test_duel_head_on_head_lower_score_loses(self):
        game = SnakeGame(10, 10, wrap=False, mode="duel", initial_food_count=3)
        a, b = game.snakes
        a.cells = deque([(4, 5), (3, 5), (2, 5)])
        a.direction = RIGHT
        a.eaten = 5
        a.pending.clear()
        b.cells = deque([(6, 5), (7, 5), (8, 5)])
        b.direction = LEFT
        b.eaten = 3
        b.pending.clear()
        game.foods = set()
        game.step()
        self.assertTrue(a.alive)    # 积分高者胜
        self.assertFalse(b.alive)
        self.assertEqual(game.status()[1], "p1")

    def test_duel_head_on_head_equal_draw(self):
        game = SnakeGame(10, 10, wrap=False, mode="duel", initial_food_count=3)
        a, b = game.snakes
        a.cells = deque([(4, 5), (3, 5), (2, 5)])
        a.direction = RIGHT
        a.eaten = 5
        a.pending.clear()
        b.cells = deque([(6, 5), (7, 5), (8, 5)])
        b.direction = LEFT
        b.eaten = 5
        b.pending.clear()
        game.foods = set()
        game.step()
        self.assertFalse(a.alive)
        self.assertFalse(b.alive)
        self.assertEqual(game.status()[1], "draw")

    def test_duel_wall_collision(self):
        game = SnakeGame(10, 10, wrap=False, mode="duel", initial_food_count=1)
        a, b = game.snakes
        a.cells = deque([(0, 2), (1, 2), (2, 2)])
        a.direction = LEFT
        a.pending.clear()
        game.foods = set()
        game.step()
        self.assertFalse(a.alive)
        self.assertTrue(b.alive)

    def test_duel_eating_removes_food(self):
        game = SnakeGame(20, 10, wrap=True, mode="duel", initial_food_count=5)
        a, b = game.snakes
        a.direction = RIGHT
        a.pending.clear()
        target = (a.head[0] + 1, a.head[1])
        game.foods = {target}
        game.step()
        self.assertEqual(a.eaten, 1)
        self.assertEqual(len(game.foods), 0)  # 吃掉的豆子消失，由定时器补充

    def test_duel_timer_result(self):
        game = SnakeGame(10, 10, mode="duel", initial_food_count=3)
        game.snakes[0].eaten = 7
        game.snakes[1].eaten = 4
        self.assertEqual(game.end_by_timer(), "p1")
        game.snakes[1].eaten = 7
        self.assertEqual(game.end_by_timer(), "draw")
        game.snakes[1].eaten = 9
        self.assertEqual(game.end_by_timer(), "p2")


if __name__ == "__main__":
    unittest.main()
