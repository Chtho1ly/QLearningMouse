# coding:utf-8

import random
import setup
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

        print 'cat init success......'

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

        print 'begin BFS......'
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
                    print seq

                    best_move = world.grid[seq[0][0]][seq[0][1]]

                q.put((ny, nx))
                step += 1
                V[(ny, nx)] = step

        if best_move is not None:
            self.cell = best_move

        else:
            dir = random.randrange(cfg.directions)
            self.go_direction(dir)
            print "!!!!!!!!!!!!!!!!!!"

    def get_value(self, mdict, key):
        try:
            return mdict[key]
        except KeyError:
            return 0

    def update(self):
        print 'cat update begin..'
        if self.cell != mouse.cell:
            self.bfs_move(mouse.cell)
            print 'cat move..'


class Cheese(setup.Agent):
    def __init__(self):
        self.color = cfg.cheese_color
        self.exist_time = 0

    def update(self):
        self.exist_time += 1
        if self.exist_time >= cfg.cheese_exist_time:
            self.exist_time = 0
            self.cell = pick_random_location()
        print 'cheese update...'
        pass


class Mouse(setup.Agent):
    def __init__(self, algorithm='qlearning', filename=cfg.graphic_file):
        # normal init
        self.catWin = 0
        self.mouseWin = 0
        self.color = cfg.mouse_color

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

        print 'mouse init...'

    def get_value(self, mdict, key):
        try:
            return mdict[key]
        except KeyError:
            return 0

    def update(self):
        print 'mouse update begin...'
        if self.algorithm != 'greedy':
            state = self.calculate_state()
            reward = cfg.MOVE_REWARD

            if self.cell == cat.cell:
                print 'eaten by cat...'
                self.catWin += 1
                reward = cfg.EATEN_BY_CAT
                if self.lastState is not None:
                    self.ai.learn(self.lastState, self.lastAction, state, reward)
                    print 'mouse learn...'
                self.lastState = None
                self.cell = pick_random_location()
                print 'mouse random generate..'
                return

            if self.cell == cheese.cell:
                self.mouseWin += 1
                reward = 50
                cheese.cell = pick_random_location()

            if self.lastState is not None:
                self.ai.learn(self.lastState, self.lastAction, state, reward)

            # choose a new action and execute it
            action = self.ai.choose_action(state)
            self.lastState = state
            self.lastAction = action
            self.go_direction(action)
        else:
            if self.cell == cat.cell:
                print 'eaten by cat...'
                self.catWin += 1
                self.lastState = None
                self.cell = pick_random_location()
                print 'mouse random generate..'
                return

            if self.cell == cheese.cell:
                self.mouseWin += 1
                cheese.cell = pick_random_location()

            # choose a new action and execute it
            self.bfs_move(cheese.cell)

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

        print 'begin BFS......'
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
                    print seq

                    best_move = world.grid[seq[0][0]][seq[0][1]]

                q.put((ny, nx))
                step += 1
                V[(ny, nx)] = step

        if best_move is not None:
            self.cell = best_move

        else:
            dir = random.randrange(cfg.directions)
            self.go_direction(dir)
            print "!!!!!!!!!!!!!!!!!!"

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
    algorithm_name = 'qlearning'
    save_file = None

    # process args
    argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv, "a:s:")
    except:
        print("Error")
    for opt, arg in opts:
        if opt in ['-a']:
            algorithm_name = arg
        elif opt in ['-s']:
            save_file = arg

    mouse = Mouse(algorithm=algorithm_name)
    if save_file:
        mouse.ai = pickle.load(open(save_file, 'rb'))
    cat = Cat(filename=cfg.graphic_file)
    cheese = Cheese()
    world = setup.World(filename=cfg.graphic_file)

    world.add_agent(mouse)
    world.add_agent(cheese, cell=pick_random_location())
    world.add_agent(cat, cell=pick_random_location())

    world.display.activate()
    world.display.speed = cfg.speed

    loop = 1
    while 1:
        world.update(mouse.mouseWin, mouse.catWin)
        loop += 1
        if loop % 1000 == 0 and algorithm_name in ['qlearning', 'sarsa']:
            with open('saves/' + mouse.algorithm + '_' + str(loop), 'wb') as f:
                pickle.dump(mouse.ai, f)
