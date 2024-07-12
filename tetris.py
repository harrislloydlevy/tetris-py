#!/usr/bin/python2

import sys, random, threading, curses, time
from curses.textpad import rectangle

class PyTrisError(Exception):
    pass

_BLOCK_TYPE_A = 0	# I-bar
_BLOCK_TYPE_B = 1	# L
_BLOCK_TYPE_C = 2	# L mirror
_BLOCK_TYPE_D = 3	# T
_BLOCK_TYPE_E = 4	# S
_BLOCK_TYPE_F = 5	# Z
_BLOCK_TYPE_G = 6	# o-block
_BLOCKS = (
    (curses.COLOR_RED, (3840, 8738)), 
    (curses.COLOR_BLUE, (3712, 17504, 11776, -15296)), 
    (curses.COLOR_MAGENTA, (1808, 12832, 18176, 8800)), 
    (curses.COLOR_GREEN, (3648, 17984, 19968, 19520)), 
    (curses.COLOR_WHITE, (864, 561)), 
    (curses.COLOR_YELLOW, (3168, 1224)), 
    (curses.COLOR_CYAN, (1632,)), 
)

_TICKS = (60, 55, 50, 45, 40, 35, 30, 25, 20)

GAME_ACTION_UP    = curses.KEY_UP
GAME_ACTION_DOWN  = curses.KEY_DOWN
GAME_ACTION_LEFT  = curses.KEY_LEFT
GAME_ACTION_RIGHT = curses.KEY_RIGHT

def getAttr(value):
    return curses.color_pair(value + 1)

class Descender:
    def __init__(self):
        self.x = 5
        self.y = 0
        self.state = 0
        self.type = random.randint(0, len(_BLOCKS) - 1)
        self.attr = getAttr(self.type)
    def getyx(self):
        return (self.y, self.x)
    def getType(self):
        return self.type
    def moveLeft(self):
        self.x -= 1
    def moveRight(self):
        self.x += 1
    def moveDown(self):
        self.y += 1
    def moveUp(self):
        self.y -= 1
    def changeState(self, reverse=False):
        if reverse:
            self.state -= 1
        else:
            self.state += 1
        self.state %= len(_BLOCKS[self.type][1])
    def getMagic(self):
        return _BLOCKS[self.type][1][self.state]
    def paint(self, win):
        '''draw self in the given curses window object.'''
        mask = 32768
        magic = self.getMagic()
        for j in range(4):
            for i in range(4):
                if mask & magic:
                    win.addstr(j, i * 2, "  ", self.attr)
                mask >>= 1
    def __str__(self):
        return "Descender type=%d, x=%d, y=%d, state=%d, magic=%d" % \
            (self.type, self.x, self.y, self.state, self.getMagic())

class Pool:
    def __init__(self, startrow=0):
        '''Initialize pool, radomly fill lowest rows.'''
        self._pool = tuple([[] for i in range(14)])
        for i in range(14):
            for j in range(22):
                if (i >= 2 and i <=11 and j <= 19):
                    self._pool[i].append(-1)
                else:
                    self._pool[i].append(-2)
        for j in range(20 - startrow, 20):
            for i in range(2, 12):
                self._pool[i][j] = random.randint(-1, \
                    len(_BLOCKS) - 1)
            self._pool[random.randint(2, 11)][j] = -1
    def isAcceptable(self, aDescender):
        '''Return true if aDescender can be accepted.'''
        y, x = aDescender.getyx()
        magic = aDescender.getMagic()
        mask = 32768
        flag = True
        for j in range(y, y+4):
            for i in range(x, x+4):
                if (magic & mask) and (self._pool[i][j] != -1):
                    flag = False
                    break
                mask >>= 1
            if not flag: break
        return flag
    def accept(self, aDescender):
        '''Add aDescender to the pool.'''
        y, x = aDescender.getyx()
        magic = aDescender.getMagic()
        mask = 32768
        t = aDescender.getType()
        for j in range(y, y+4):
            for i in range(x, x+4):
                if magic & mask:
                    self._pool[i][j] = t
                mask >>= 1
    def clean(self, y=0):
        '''Return number of line get cleared.'''
        cleared = 0
        for j in range(y, y+4):
            flag = True
            for i in range(2, 12):
                if self._pool[i][j] < 0:
                    flag = False
                    break
            if flag:
                #curses.flash()
                for i in range(2, 12):
                    for k in range(j, 0, -1):
                        self._pool[i][k] = self._pool[i][k-1]
                    self._pool[i][0] = -1
                cleared += 1
        return cleared
    def paint(self, win):
        '''Paint self in the given curses window object.'''
        for j in range(20):
            for i in range(2, 12):	
                win.addstr(j, (i - 2) * 2, "  ", \
                    getAttr(self._pool[i][j]))
    def __str__(self):
        s = ""
        for j in range(22):
            for i in range(14):
                s += "% 2d " % self._pool[i][j]
            s += "\n"
        return s
# end of class Pool

class TimerThread(threading.Thread):
    def __init__(self, gameMgr):
        threading.Thread.__init__(self)
        self.gameMgr = gameMgr
        self.setName = "Game timer"
    def run(self):
        while not self.gameMgr.paused:
            time.sleep(0.01)
            self.gameMgr.run()

class PyTrisGame:
    def __init__(self, win, startrow=0, startlevel=1, preview=True):
        self.win     = win
        self.level   = startlevel
        self.preview = preview
        self.pool    = Pool(startrow)
        self.ap      = Descender()
        self.np      = Descender()
        self.score   = 0
        self.tick    = 0
        self.paused  = True
        self.timer   = None
        self.prevwin = win.subwin(4, 8, 3, 2)
        self.poolwin = win.subwin(20, 21, 1, 13)
        self.paint()
    def _paintPrev(self):
        uly, ulx = self.prevwin.getbegyx()
        lry, lrx = self.prevwin.getmaxyx()
        lry += uly; lrx += ulx
        rectangle(self.win, uly - 1, ulx - 1, lry, lrx)
        self.np.paint(self.prevwin)
        #self.prevwin.refresh()
    def _paintScore(self):
        self.win.attron(curses.A_BOLD)
        self.win.addstr(15, 2, "Score".center(9))
        self.win.addstr(18, 2, "Level".center(9))
        self.win.attroff(curses.A_BOLD)
        self.win.addstr(16, 2, ("%d" % self.score).center(9))
        self.win.addstr(19, 2, ("%d" % self.level).center(9))
    def _paintPool(self):
        uly, ulx = self.poolwin.getbegyx()
        lry, lrx = self.poolwin.getmaxyx()
        lry += uly; lrx += ulx
        rectangle(self.win, uly - 1, ulx - 1, lry, lrx - 1)
        self.pool.paint(self.poolwin)
        self.poolwin.refresh()
    def _paintPiece(self):
        y, x = self.ap.getyx()
        by, bx = self.poolwin.getbegyx()
        y += by
        x = (x - 2) * 2 + bx
        # allow more more column for block S state 1
        w = self.win.subwin(4, 9, y, x)
        self.ap.paint(w)
        w.refresh()
    def paint(self):
        self.win.clear()
        #curses.beep()
        if self.preview: self._paintPrev()
        self._paintScore()
        self._paintPool()
        self._paintPiece()
    def startGame(self):
        '''create timer thread.'''
        self.paused = False
        self.timer = TimerThread(self)
        self.timer.start()
    def pauseGame(self):
        '''set pause flag to stop timer.'''
        self.paused = True
        self.timer.join()
        self.timer = None
    def stopGame(self):
        '''stop game when game is over.'''
        self.paused = True
    def run(self):
        '''callback routine for GameTimer.'''
        self.tick = (self.tick + 1) % _TICKS[self.level - 1]
        if self.tick == 0:
            self.handleGameAction(GAME_ACTION_DOWN)
    def changePiece(self):
        y, x = self.ap.getyx()
        lc = self.pool.clean(y)
        self.score += lc * 100
        if self.pool.isAcceptable(self.np):
            self.ap = self.np
            self.np = Descender()
        else:
            self.stopGame()
    def handleGameAction(self, act):
        _lock.acquire()
        if act == GAME_ACTION_LEFT:
            self.ap.moveLeft()
            if self.pool.isAcceptable(self.ap):
                self.paint()
            else:
                self.ap.moveRight()
        elif act == GAME_ACTION_RIGHT:
            self.ap.moveRight()
            if self.pool.isAcceptable(self.ap):
                self.paint()
            else:
                self.ap.moveLeft()
        elif act == GAME_ACTION_UP:
            self.ap.changeState()
            if self.pool.isAcceptable(self.ap):
                self.paint()
            else:
                self.ap.changeState(True)
        elif act == GAME_ACTION_DOWN:
            self.ap.moveDown()
            if not self.pool.isAcceptable(self.ap):
                self.ap.moveUp()
                self.pool.accept(self.ap)
                self.changePiece()
            self.paint()
        _lock.release()

_lock = None

def main(stdscr):
    global _lock
    # check terminal size
    h, w = stdscr.getmaxyx()
    if w < 34 or h < 22: raise PyTrisError, \
        "Terminal size must be greater than 34x22"

    # initialize color pairs
    for i in range(1, len(_BLOCKS) + 1):
        curses.init_pair(i, curses.COLOR_WHITE, _BLOCKS[i - 1][0])
    curses.init_pair(20, curses.COLOR_BLACK, curses.COLOR_WHITE)

    # allocate RLock
    _lock = threading.RLock()
    assert _lock

    # start a new game
    startrow = 5
    startlevel = 1
    preview = True
    gameMgr = PyTrisGame(stdscr, startrow, startlevel, preview)
    gameMgr.startGame()
    while 1:
        c = stdscr.getch()
        if c == ord("q"):
            gameMgr.pauseGame()
            break
        elif c == curses.KEY_RESIZE:
            gameMgr.paint()
        else:
            gameMgr.handleGameAction(c)
        time.sleep(0.000001)

# end of main

if __name__ == "__main__":
    try:
        try:
            stdscr=curses.initscr()
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(1)
            curses.curs_set(0)
            try:
                curses.start_color()
            except:
                pass
            main(stdscr)
        finally:
            curses.curs_set(1)
            stdscr.keypad(0)
            curses.echo()
            curses.nocbreak()
            curses.endwin()
    except PyTrisError, e:
        print >> sys.stderr, e
    else:
        print "Thank you for playing pytris"
# end of program
