"""迷宫生成器与渲染器测试。"""

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from maze.config import SIZE_KEYS, load_settings
from maze.generator import ALGORITHMS, generate_maze
from maze.pathfinding import find_path
from maze.renderer import render_to_file


class GeneratorTests(unittest.TestCase):
    def test_all_algorithms_produce_perfect_mazes(self):
        for algorithm in ALGORITHMS:
            with self.subTest(algorithm=algorithm):
                maze = generate_maze(12, 9, algorithm=algorithm, seed=1)
                self.assertTrue(maze.is_perfect())

    def test_all_preset_sizes(self):
        settings = load_settings()
        for key in SIZE_KEYS:
            with self.subTest(size=key):
                preset = settings.get_preset(key)
                maze = generate_maze(preset.width, preset.height, seed=1)
                self.assertTrue(maze.is_perfect())
                self.assertEqual(maze.width, preset.width)
                self.assertEqual(maze.height, preset.height)

    def test_seed_determinism(self):
        a = generate_maze(15, 12, seed=42)
        b = generate_maze(15, 12, seed=42)
        self.assertEqual(a.walls, b.walls)
        self.assertEqual(a.seed, b.seed)

    def test_different_seeds_usually_differ(self):
        results = {
            tuple(tuple(row) for row in generate_maze(8, 8).walls) for _ in range(5)
        }
        self.assertGreater(len(results), 1)

    def test_invalid_dimensions(self):
        with self.assertRaises(ValueError):
            generate_maze(1, 1)

    def test_invalid_algorithm(self):
        with self.assertRaises(ValueError):
            generate_maze(5, 5, algorithm="unknown")


class RendererTests(unittest.TestCase):
    def test_render_png_dimensions(self):
        settings = load_settings()
        preset = settings.get_preset("small")
        maze = generate_maze(preset.width, preset.height, seed=7)
        with tempfile.TemporaryDirectory() as tmp:
            out = render_to_file(
                maze, settings.style, preset.cell_size, Path(tmp) / "maze.png"
            )
            self.assertTrue(out.is_file())
            with Image.open(out) as img:
                expected_w = preset.cell_size * preset.width + 2 * settings.style.margin
                expected_h = preset.cell_size * preset.height + 2 * settings.style.margin
                self.assertEqual(img.size, (expected_w, expected_h))


class PathfindingTests(unittest.TestCase):
    def test_path_reaches_every_cell_without_walls(self):
        maze = generate_maze(20, 15, seed=3)
        for y in range(maze.height):
            for x in range(maze.width):
                with self.subTest(cell=(x, y)):
                    path = find_path(maze, (0, 0), (x, y))
                    self.assertIsNotNone(path)
                    self.assertEqual(path[0], (0, 0))
                    self.assertEqual(path[-1], (x, y))
                    for a, b in zip(path, path[1:]):
                        self.assertIn(b, list(maze.neighbors(*a)))

    def test_out_of_bounds_returns_none(self):
        maze = generate_maze(8, 8, seed=1)
        self.assertIsNone(find_path(maze, (0, 0), (99, 99)))

    def test_same_start_and_goal(self):
        maze = generate_maze(8, 8, seed=1)
        self.assertEqual(find_path(maze, (3, 3), (3, 3)), [(3, 3)])


if __name__ == "__main__":
    unittest.main()
