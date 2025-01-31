# coding:utf-8

import random
import setup_UIless as setup
import RL
import config as cfg
import pickle
import sys
import getopt
from Queue import Queue

reload(setup)
reload(RL)


def pick_random_location():
    while 1:
        x = random.randrange(world.width)
        y = random.randrange(world.height)
        cell = world.get_cell(x, y)
        if not (cell.wall or len(cell.agents) > 0):
            return cell


class Cat(setup.Agent):
    def __init__(self, filename):
        self.cell = None
        self.catWin = 0
        self.color = cfg.cat_color
        f = file(filename)
        lines = f.readlines()
        lines = [x.rstrip() for x in lines]
        self.fh = len(lines)
        self.fw = max([len(x) for x in lines])
        self.grid_list = [[1 for x in xrange(self.fw)] for y in xrange(self.fh)]
        self.move = [(0, -1), (1, -1), (
            1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]

        for y in xrange(self.fh):
            line = lines[y]
            for x in xrange(min(self.fw, len(line))):
                t = 1 if (line[x] == 'X') else 0
                self.grid_list[y][x] = t

        # print 'cat init success......'

    # using BFS algorithm to move quickly to target.
    def bfs_move(self, target):
        if self.cell == target:
            return

        for n in self.cell.neighbors:
            if n == target:
                self.cell = target  # if next move can go towards target
                return

        best_move = None
        q = Queue()
        start = (self.cell.y, self.cell.x)
        end = (target.y, target.x)
        q.put(start)
        step = 1
        V = {}
        preV = {}
        V[(start[0], start[1])] = 1

        # print 'begin BFS......'
        while not q.empty():
            grid = q.get()

            for i in xrange(8):
                ny, nx = grid[0] + self.move[i][0], grid[1] + self.move[i][1]
                if nx < 0 or ny < 0 or nx > (self.fw - 1) or ny > (self.fh - 1):
                    continue
                if self.get_value(V, (ny, nx)) or self.grid_list[ny][nx] == 1:  # has visit or is wall.
                    continue

                preV[(ny, nx)] = self.get_value(V, (grid[0], grid[1]))
                if ny == end[0] and nx == end[1]:
                    V[(ny, nx)] = step + 1
                    seq = []
                    last = V[(ny, nx)]
                    while last > 1:
                        k = [key for key in V if V[key] == last]
                        seq.append(k[0])
                        assert len(k) == 1
                        last = preV[(k[0][0], k[0][1])]
                    seq.reverse()
                    # print seq

                    best_move = world.grid[seq[0][0]][seq[0][1]]

                q.put((ny, nx))
                step += 1
                V[(ny, nx)] = step

        if best_move is not None:
            self.cell = best_move

        else:
            dir = random.randrange(cfg.directions)
            self.go_direction(dir)
            # print "!!!!!!!!!!!!!!!!!!"

    def get_value(self, mdict, key):
        try:
            return mdict[key]
        except KeyError:
            return 0

    def update(self):
        # print 'cat update begin..'
        if self.cell != mouse.cell:
            self.bfs_move(mouse.cell)
            # print 'cat move..'


class Cheese(setup.Agent):
    def __init__(self):
        self.color = cfg.cheese_color
        self.exist_time = 0
        self.refresh = False

    def update(self):
        self.exist_time += 1
        if self.exist_time >= cfg.cheese_exist_time:
            self.exist_time = 0
            self.refresh = True
            self.cell = pick_random_location()
        # print 'cheese update...'
        pass


class Mouse(setup.Agent):
    def __init__(self, algorithm='qlearning', filename=cfg.graphic_file):
        # normal init
        self.catWin = 0
        self.mouseWin = 0
        self.color = cfg.mouse_color
        self.survive_time = 0
        self.total_reward = 0

        # init for RL
        self.ai = None
        self.algorithm = algorithm
        if algorithm == 'qlearning':
            self.ai = RL.QLearn(actions=xrange(cfg.directions), alpha=0.1, gamma=0.9, epsilon=0.1)
        elif algorithm == 'sarsa':
            self.ai = RL.SARSA(actions=xrange(cfg.directions), alpha=0.1, gamma=0.9, epsilon=0.1)
        self.lastState = None
        self.lastAction = None

        # init for greedy
        f = file(filename)
        lines = f.readlines()
        lines = [x.rstrip() for x in lines]
        self.fh = len(lines)
        self.fw = max([len(x) for x in lines])
        self.grid_list = [[1 for x in xrange(self.fw)] for y in xrange(self.fh)]
        self.move = [(0, -1), (1, -1), (
            1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
        for y in xrange(self.fh):
            line = lines[y]
            for x in xrange(min(self.fw, len(line))):
                t = 1 if (line[x] == 'X') else 0
                self.grid_list[y][x] = t

        # print 'mouse init...'

    def get_value(self, mdict, key):
        try:
            return mdict[key]
        except KeyError:
            return 0

    def update(self):
        # print 'mouse update begin...'
        self.survive_time += 1
        if self.algorithm != 'greedy':
            state = self.calculate_state()
            reward = cfg.MOVE_REWARD

            if self.cell == cat.cell:
                # print 'eaten by cat...'
                self.catWin += 1
                reward = cfg.EATEN_BY_CAT
                self.lastState = None
                self.cell = pick_random_location()
                # print 'mouse random generate..'
                self.total_reward += reward
                return

            if self.cell == cheese.cell:
                self.mouseWin += 1
                reward = 50
                cheese.cell = pick_random_location()

            # choose a new action and execute it
            action = self.ai.choose_action(state)
            self.lastState = state
            self.lastAction = action
            self.go_direction(action)
            self.total_reward += reward
        else:
            reward = cfg.MOVE_REWARD
            if self.cell == cat.cell:
                # print 'eaten by cat...'
                self.catWin += 1
                reward = cfg.EATEN_BY_CAT
                self.lastState = None
                self.cell = pick_random_location()
                # print 'mouse random generate..'
                return

            if self.cell == cheese.cell:
                self.mouseWin += 1
                reward = cfg.EAT_CHEESE
                cheese.cell = pick_random_location()

            # choose a new action and execute it
            self.bfs_move(cheese.cell)
            self.total_reward += reward

    # using BFS algorithm to move quickly to target.
    def bfs_move(self, target):
        if self.cell == target:
            return

        for n in self.cell.neighbors:
            if n == target:
                self.cell = target  # if next move can go towards target
                return

        best_move = None
        q = Queue()
        start = (self.cell.y, self.cell.x)
        end = (target.y, target.x)
        q.put(start)
        step = 1
        V = {}
        preV = {}
        V[(start[0], start[1])] = 1

        # print 'begin BFS......'
        while not q.empty():
            grid = q.get()

            for i in xrange(8):
                ny, nx = grid[0] + self.move[i][0], grid[1] + self.move[i][1]
                if nx < 0 or ny < 0 or nx > (self.fw - 1) or ny > (self.fh - 1):
                    continue
                if self.get_value(V, (ny, nx)) or self.grid_list[ny][nx] == 1:  # has visit or is wall.
                    continue

                preV[(ny, nx)] = self.get_value(V, (grid[0], grid[1]))
                if ny == end[0] and nx == end[1]:
                    V[(ny, nx)] = step + 1
                    seq = []
                    last = V[(ny, nx)]
                    while last > 1:
                        k = [key for key in V if V[key] == last]
                        seq.append(k[0])
                        assert len(k) == 1
                        last = preV[(k[0][0], k[0][1])]
                    seq.reverse()
                    # print seq

                    best_move = world.grid[seq[0][0]][seq[0][1]]

                q.put((ny, nx))
                step += 1
                V[(ny, nx)] = step

        if best_move is not None:
            self.cell = best_move

        else:
            dir = random.randrange(cfg.directions)
            self.go_direction(dir)
            # print "!!!!!!!!!!!!!!!!!!"

    def calculate_state(self):
        def cell_value(cell):
            if cat.cell is not None and (cell.x == cat.cell.x and cell.y == cat.cell.y):
                return 3
            elif cheese.cell is not None and (cell.x == cheese.cell.x and cell.y == cheese.cell.y):
                return 2
            else:
                return 1 if cell.wall else 0

        dirs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        cheese_dis = [cheese.cell.x - mouse.cell.x, cheese.cell.y - mouse.cell.y]
        cheese_dir = 0
        if abs(cheese_dis[0]) > abs(cheese_dis[1]):
            if cheese_dis[0] > 0:
                cheese_dir = 1
            else:
                cheese_dir = 2
        else:
            if cheese_dis[1] > 0:
                cheese_dir = 3
            else:
                cheese_dir = 4

        state = tuple([cell_value(world.get_relative_cell(self.cell.x + dir[0], self.cell.y + dir[1])) for dir in
                       dirs]) + tuple([cheese_dir])
        # print state
        return state


if __name__ == '__main__':
    algorithm_names = ['greedy', 'sarsa', 'qlearning']
    # algorithm_names = ['qlearning']
    step = 8000
    train_times = range(step, 800000 + 1, step)

    result_file_path = 'csv/result.csv'
    with open(result_file_path, 'w') as result_file:
        # table head
        result_file.write(',')
        for algorithm_name in algorithm_names:
            result_file.write('%s_reward,' % algorithm_name)
            result_file.write('%s_survive,' % algorithm_name)
            result_file.write('%s_mouse,' % algorithm_name)
            result_file.write('%s_cat,' % algorithm_name)
        result_file.write('\n')

        for train_time in train_times:
            result_file.write('%d,' % train_time)
            for algorithm_name in algorithm_names:
                save_file = 'saves/' + algorithm_name + '_' + str(train_time)
                total_reward = 0
                total_survive = 0
                total_cat_win = 0
                total_mouse_win = 0
                for i in range(cfg.test_time):
                    mouse = Mouse(algorithm=algorithm_name)
                    if algorithm_name in ['sarsa', 'qlearning']:
                        mouse.ai = pickle.load(open(save_file, 'rb'))
                    cat = Cat(filename=cfg.graphic_file)
                    cheese = Cheese()
                    world = setup.World(filename=cfg.graphic_file)

                    world.add_agent(mouse)
                    world.add_agent(cheese, cell=pick_random_location())
                    world.add_agent(cat, cell=pick_random_location())

                    # world.display.activate()
                    # world.display.speed = cfg.speed

                    while not (mouse.mouseWin or mouse.catWin or cheese.refresh):
                        world.update(mouse.mouseWin, mouse.catWin)

                    # world.display.quit()
                    total_reward += mouse.total_reward
                    total_survive += mouse.survive_time
                    total_mouse_win += mouse.mouseWin
                    total_cat_win += mouse.catWin

                print('%12s%8d%8.2f%8.2f%8.2f%8.2f'
                      % (algorithm_name, train_time,
                         total_reward / float(cfg.test_time),
                         total_survive / float(cfg.test_time),
                         total_mouse_win / float(cfg.test_time),
                         total_cat_win / float(cfg.test_time)))
                result_file.write('%.2f,%.2f,%.2f,%.2f,'
                                  % (total_reward / float(cfg.test_time),
                                     total_survive / float(cfg.test_time),
                                     total_mouse_win / float(cfg.test_time),
                                     total_cat_win / float(cfg.test_time)))
            result_file.write('\n')
