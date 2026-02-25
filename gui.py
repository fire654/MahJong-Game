"""
麻将可视化 - pygame 版本
依赖：pip install pygame
运行：python mahjong_gui.py
"""

import pygame
import random
import copy
import sys
import time

# ══════════════════════════════════════════════
#  常量 & 配色
# ══════════════════════════════════════════════

W, H = 1280, 800

# 颜色
C_BG        = (15, 40, 25)       # 深绿桌布背景
C_FELT      = (22, 58, 36)       # 桌布纹理色
C_TILE_FACE = (255, 248, 220)    # 牌面 - 象牙白
C_TILE_BACK = (180, 60, 60)      # 牌背 - 深红
C_TILE_SEL  = (255, 230, 80)     # 选中高亮
C_TILE_HVR  = (240, 240, 200)    # hover
C_SHADOW    = (0, 0, 0, 100)
C_TEXT_DARK = (40, 30, 20)
C_TEXT_LITE = (230, 220, 200)
C_TEXT_GOLD = (220, 180, 60)
C_TEXT_RED  = (200, 60, 60)
C_TEXT_GRN  = (80, 200, 120)
C_BTN_NORM  = (50, 90, 60)
C_BTN_HOV   = (70, 130, 85)
C_BTN_DIS   = (40, 60, 45)
C_BTN_ACT   = (180, 140, 40)     # 可操作按钮高亮
C_DISCARD   = (30, 55, 38)
C_PANEL     = (18, 45, 28)
C_BORDER    = (80, 120, 70)

# 牌尺寸
TW, TH = 46, 64      # 手牌
STW, STH = 34, 48    # 小牌（弃牌区）
BTW, BTH = 36, 52    # 机器人背面牌

# 花色中文符号和颜色
SUIT_SYMBOL = {'S': '条', 'M': '万', 'P': '饼'}
SUIT_COLOR  = {'S': (60, 160, 80), 'M': (200, 60, 60), 'P': (60, 100, 200)}

# ══════════════════════════════════════════════
#  游戏逻辑（独立于 GUI）
# ══════════════════════════════════════════════

class Player:
    def __init__(self, pid):
        self.pid = pid
        self.hand = []
        self.sub_hand = []
        self.discard_pile = []

    def draw(self, card): self.hand.append(card)

    def discard(self, card):
        self.hand.remove(card)
        self.discard_pile.append(card)

    def sort_hand(self):
        self.hand.sort(key=lambda x: (x[0], int(x[1])))

    def peng(self, card):
        if self.hand.count(card) >= 2:
            self.sub_hand.append([card]*3)
            self.hand.remove(card); self.hand.remove(card)
            return True
        return False

    def gang1(self, card):
        if self.hand.count(card) >= 3:
            self.sub_hand.append([card]*4)
            for _ in range(3): self.hand.remove(card)
            return True
        return False

    def gang0(self, card):
        if self.hand.count(card) >= 4:
            self.sub_hand.append([card]*4)
            for _ in range(4): self.hand.remove(card)
            return True
        return False

    def gang2(self, card):
        if [card]*3 in self.sub_hand and self.hand.count(card) == 1:
            self.sub_hand.remove([card]*3)
            self.sub_hand.append([card]*4)
            self.hand.remove(card)
            self.discard_pile.append(card)
            return True
        return False

    @staticmethod
    def is_valid_chow(chow):
        """判断三张牌是否构成合法顺子"""
        if len(chow) != 3:
            return False
        suits = [c[0] for c in chow]
        ranks = sorted(int(c[1]) for c in chow)
        # 同花色且连续
        return suits[0] == suits[1] == suits[2] and ranks[1]-ranks[0] == 1 and ranks[2]-ranks[1] == 1

    def chi(self, card, chow):
        if not self.is_valid_chow(chow):
            return False
        others = [c for c in chow if c != card]
        # 去重处理：确保 others 中重复牌手里有足够数量
        needed = {}
        for c in others:
            needed[c] = needed.get(c, 0) + 1
        if not all(self.hand.count(c) >= n for c, n in needed.items()):
            return False
        for c in others:
            self.hand.remove(c)
        self.sub_hand.append(sorted(chow, key=lambda x:(x[0],int(x[1]))))
        return True

    def _hu_list(self, a):
        a = list(a)
        if all(x == 0 for x in a): return 1
        i = next((j for j,x in enumerate(a) if x), None)
        if a[i] < 3:
            if len(a) >= i+3 and a[i+1] and a[i+2]:
                a[i]-=1; a[i+1]-=1; a[i+2]-=1
                return self._hu_list(a)
            return 0
        else:
            if len(a) >= i+3 and a[i+1] and a[i+2]:
                b = list(a); b[i]-=3
                a[i]-=1; a[i+1]-=1; a[i+2]-=1
                return max(self._hu_list(a), self._hu_list(b))
            a[i]-=3
            return self._hu_list(a)

    def is_hu(self, tiles):
        cnt = {'S':[0]*9,'M':[0]*9,'P':[0]*9}
        for t in tiles: cnt[t[0]][int(t[1])-1] += 1
        for suit in cnt:
            for i in range(9):
                if cnt[suit][i] >= 2:
                    cnt[suit][i] -= 2
                    S = self._hu_list(cnt['S'][:])
                    M = self._hu_list(cnt['M'][:])
                    P = self._hu_list(cnt['P'][:])
                    if S*M*P == 1: return True
                    cnt[suit][i] += 2
        return False

    def can_hu(self): return self.is_hu(self.hand)
    def can_hu_with(self, card): return self.is_hu(self.hand + [card])


class RobotPlayer(Player):
    def decide_discard(self):
        # 简单策略：随机弃牌
        card = random.choice(self.hand)
        self.discard(card)
        return card

    def auto_move(self):
        for c in set(self.hand):
            if self.gang0(c): return ('gang0', c)
        for c in set(self.hand):
            if self.gang2(c): return ('gang2', c)
        return ('discard', self.decide_discard())

    def respond(self, card, is_next):
        if self.can_hu_with(card): return 'hu'
        if is_next:
            for c1 in self.hand:
                for c2 in self.hand:
                    if c1 == c2: continue
                    for chow in [[c1,c2,card],[c1,card,c2],[card,c1,c2]]:
                        cs = sorted(chow, key=lambda x:(x[0],int(x[1])))
                        if (cs[0][0]==cs[1][0]==cs[2][0] and
                            int(cs[1][1])-int(cs[0][1])==1 and
                            int(cs[2][1])-int(cs[1][1])==1):
                            self.chi(card, chow)
                            return 'chi'
        if self.peng(card): return 'peng'
        if self.gang1(card): return 'gang1'
        return 'pass'


class GameLogic:
    def __init__(self):
        self.deck = self._make_deck()
        self.players = [Player(0)] + [RobotPlayer(i) for i in range(1,4)]
        self.cur = 0
        self.deal()

    def _make_deck(self):
        d = [s+r for s in 'SMP' for r in '123456789'] * 4
        random.shuffle(d)
        return d

    def deal(self):
        for _ in range(13):
            for p in self.players:
                p.draw(self.deck.pop())
        self.players[0].sort_hand()

    def draw(self):
        return self.deck.pop() if self.deck else None

    def remaining(self):
        return len(self.deck)

# ══════════════════════════════════════════════
#  GUI 组件
# ══════════════════════════════════════════════

class Button:
    def __init__(self, rect, label, color=C_BTN_NORM, active=True):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.color = color
        self.active = active
        self.hovered = False

    def draw(self, surf, font):
        c = self.color if self.active else C_BTN_DIS
        if self.active and self.hovered:
            c = tuple(min(255, x+30) for x in c[:3])
        # 阴影
        shadow = self.rect.move(3,3)
        pygame.draw.rect(surf, (0,0,0,80), shadow, border_radius=8)
        pygame.draw.rect(surf, c, self.rect, border_radius=8)
        pygame.draw.rect(surf, C_BORDER, self.rect, 2, border_radius=8)
        tc = C_TEXT_GOLD if self.active else (100,110,100)
        txt = font.render(self.label, True, tc)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def check(self, pos):
        self.hovered = self.rect.collidepoint(pos)
        return self.hovered

    def clicked(self, pos):
        return self.active and self.rect.collidepoint(pos)


def draw_tile(surf, card, x, y, w=TW, h=TH, selected=False, hover=False, face_up=True):
    """绘制一张牌"""
    rect = pygame.Rect(x, y, w, h)

    # 阴影
    pygame.draw.rect(surf, (0,0,0), rect.move(3,3), border_radius=6)

    if not face_up:
        pygame.draw.rect(surf, C_TILE_BACK, rect, border_radius=6)
        pygame.draw.rect(surf, (150,40,40), rect, 2, border_radius=6)
        # 背面花纹
        inner = rect.inflate(-8,-8)
        pygame.draw.rect(surf, (160,50,50), inner, 2, border_radius=4)
        return

    bg = C_TILE_SEL if selected else (C_TILE_HVR if hover else C_TILE_FACE)
    pygame.draw.rect(surf, bg, rect, border_radius=6)
    pygame.draw.rect(surf, (180,170,140), rect, 2, border_radius=6)

    if card:
        suit, rank = card[0], card[1]
        sc = SUIT_COLOR[suit]
        # 数字
        nf = pygame.font.SysFont('SimHei', int(h*0.38), bold=True)
        nt = nf.render(rank, True, sc)
        surf.blit(nt, nt.get_rect(centerx=x+w//2, top=y+4))
        # 花色
        sf = pygame.font.SysFont('SimHei', int(h*0.28))
        st = sf.render(SUIT_SYMBOL[suit], True, sc)
        surf.blit(st, st.get_rect(centerx=x+w//2, bottom=y+h-4))


def draw_tile_group(surf, group, x, y, w=STW, h=STH):
    """绘制副露牌组（带方框）"""
    total_w = len(group) * (w+2) + 6
    pygame.draw.rect(surf, (60,100,70), (x-3, y-3, total_w, h+6), border_radius=4)
    for i, card in enumerate(group):
        draw_tile(surf, card, x + i*(w+2), y, w, h)


# ══════════════════════════════════════════════
#  主 GUI 类
# ══════════════════════════════════════════════

class MahjongGUI:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption('麻将')

        self.font_sm  = pygame.font.SysFont('SimHei', 16)
        self.font_md  = pygame.font.SysFont('SimHei', 20, bold=True)
        self.font_lg  = pygame.font.SysFont('SimHei', 28, bold=True)
        self.font_xl  = pygame.font.SysFont('SimHei', 48, bold=True)
        self.font_btn = pygame.font.SysFont('SimHei', 18, bold=True)

        self.game = GameLogic()
        self.state = 'player_turn'   # player_turn / robot_turn / response / chi_select / game_over
        self.selected_card = None    # 玩家0选中要出的牌
        self.hover_card = None
        self.last_discard = None
        self.discarder = None
        self.message = ''
        self.message_timer = 0
        self.robot_timer = 0         # 机器人动作延迟
        self.robot_step = 0
        self.game_over_msg = ''
        self.chi_candidates = []     # 吃牌候选顺子
        self.chi_selected = []
        self.buttons = []
        self.drawn_card = None       # 本回合摸到的牌
        self.response_queue = []     # 待响应的玩家列表
        self.winning_player = -1

        self._start_player_turn()

    # ──────────────────────── 回合管理 ────────────────────────

    def _start_player_turn(self):
        self.game.cur = 0
        card = self.game.draw()
        if card is None:
            self._end_game('流局 - 牌堆已空')
            return
        self.drawn_card = card
        self.game.players[0].draw(card)
        self.game.players[0].sort_hand()
        self.state = 'player_turn'
        self._set_message(f'摸到：{card}')
        self._build_player_buttons()

    def _build_player_buttons(self):
        p = self.game.players[0]
        btns = []
        # 检查可用操作
        can_hu = p.can_hu()
        can_angang = any(p.hand.count(c) >= 4 for c in set(p.hand))
        can_bugang = any([c]*3 in p.sub_hand and p.hand.count(c) >= 1 for c in set(p.hand))

        bw, bh, bx, by, gap = 100, 38, 640, 735, 12
        defs = [
            ('胡 (H)',    'hu',    C_BTN_ACT if can_hu else C_BTN_NORM,    can_hu),
            ('出牌 (点击手牌)', 'info', C_BTN_NORM, False),
            ('暗杠 (G)',  'gang0', C_BTN_ACT if can_angang else C_BTN_NORM, can_angang),
            ('补杠 (B)',  'gang2', C_BTN_ACT if can_bugang else C_BTN_NORM, can_bugang),
            ('理牌 (R)',  'sort',  C_BTN_NORM, True),
            ('查询 (Q)',  'query', C_BTN_NORM, True),
        ]
        for i, (lbl, tag, col, act) in enumerate(defs):
            btn = Button((bx + i*(bw+gap), by, bw, bh), lbl, col, act)
            btn.tag = tag
            btns.append(btn)
        self.buttons = btns

    def _build_response_buttons(self, can_chi=False):
        p = self.game.players[0]
        card = self.last_discard
        can_hu = p.can_hu_with(card) if card else False
        can_peng = p.hand.count(card) >= 2 if card else False
        can_gang = p.hand.count(card) >= 3 if card else False

        btns = []
        bw, bh, bx, by, gap = 100, 38, 490, 735, 12
        defs = [
            ('胡',   'hu',   C_BTN_ACT if can_hu else C_BTN_NORM,   can_hu),
            ('吃',   'chi',  C_BTN_ACT if can_chi else C_BTN_NORM,   can_chi),
            ('碰',   'peng', C_BTN_ACT if can_peng else C_BTN_NORM,  can_peng),
            ('杠',   'gang1',C_BTN_ACT if can_gang else C_BTN_NORM,  can_gang),
            ('跳过', 'pass', C_BTN_NORM, True),
            ('理牌', 'sort', C_BTN_NORM, True),
        ]
        for i, (lbl, tag, col, act) in enumerate(defs):
            btn = Button((bx + i*(bw+gap), by, bw, bh), lbl, col, act)
            btn.tag = tag
            btns.append(btn)
        self.buttons = btns

    def _start_robot_turn(self, pid):
        self.game.cur = pid
        self.state = 'robot_turn'
        self.robot_step = 0
        self.robot_timer = pygame.time.get_ticks()
        self.buttons = []

    def _advance_turn(self):
        """轮到下一个玩家"""
        self.game.cur = (self.game.cur + 1) % 4
        if self.game.cur == 0:
            self._start_player_turn()
        else:
            self._start_robot_turn(self.game.cur)

    # ──────────────────────── 响应阶段 ────────────────────────

    def _start_response_phase(self, discard_card, discarder_idx):
        """某人打牌后，其他人依次响应"""
        self.last_discard = discard_card
        self.discarder = discarder_idx
        self.response_queue = [(discarder_idx + k) % 4 for k in range(1, 4)]
        self._process_response_queue()

    def _process_response_queue(self):
        if not self.response_queue:
            # 所有人跳过，轮到下一家
            self.game.cur = (self.discarder + 1) % 4
            if self.game.cur == 0:
                self._start_player_turn()
            else:
                self._start_robot_turn(self.game.cur)
            return

        j = self.response_queue[0]

        if j == 0:
            # 玩家0响应
            is_next = (j == (self.discarder + 1) % 4)
            self.state = 'response'
            self._build_response_buttons(can_chi=is_next)
        else:
            # 机器人响应
            robot = self.game.players[j]
            is_next = (j == (self.discarder + 1) % 4)
            result = robot.respond(self.last_discard, is_next)
            self.response_queue.pop(0)

            if result == 'hu':
                self._set_message(f'玩家{j} 胡！')
                self._end_game(f'玩家 {j} 点炮胡牌！', winner=j)
            elif result in ('chi','peng'):
                action = '吃' if result == 'chi' else '碰'
                self._set_message(f'玩家{j} {action} {self.last_discard}')
                self.game.cur = j
                card = robot.decide_discard()
                self._set_message(f'玩家{j} 打出 {card}')
                self._start_response_phase(card, j)
            elif result == 'gang1':
                self._set_message(f'玩家{j} 杠 {self.last_discard}')
                self.game.cur = j
                self._start_robot_turn(j)
            else:
                self._process_response_queue()

    # ──────────────────────── 事件处理 ────────────────────────

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()

        mouse = pygame.mouse.get_pos()
        for btn in self.buttons:
            btn.check(mouse)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(mouse)

        if event.type == pygame.KEYDOWN:
            self._handle_key(event.key)

    def _handle_click(self, pos):
        for btn in self.buttons:
            if btn.clicked(pos):
                self._handle_button(btn.tag)
                return

        if self.state == 'player_turn':
            # 点击手牌
            card, _ = self._get_card_at(pos, self.game.players[0].hand, *self._hand_pos(0))
            if card:
                if self.selected_card == card:
                    # 二次点击 = 出牌
                    self._player_discard(card)
                else:
                    self.selected_card = card

        elif self.state == 'chi_select':
            # 点击选顺子
            card, _ = self._get_card_at(pos, self.game.players[0].hand, *self._hand_pos(0))
            if card and card != self.last_discard:
                # 只允许选同花色的牌
                if card[0] != self.last_discard[0]:
                    self._set_message(f'吃牌必须同花色（{self.last_discard[0]}）')
                elif card in self.chi_selected:
                    self.chi_selected.remove(card)
                    self._set_message(f'已取消选择 {card}，请重新选')
                else:
                    self.chi_selected.append(card)
                    remaining = 2 - len(self.chi_selected)
                    if remaining > 0:
                        self._set_message(f'已选 {card}，还需选 {remaining} 张')

                if len(self.chi_selected) == 2:
                    chow = self.chi_selected + [self.last_discard]
                    # 提前预检，给出明确错误
                    if not Player.is_valid_chow(chow):
                        self._set_message(f'{"、".join(self.chi_selected)} 与 {self.last_discard} 不构成顺子，重选')
                        self.chi_selected = []
                    elif self.game.players[0].chi(self.last_discard, chow):
                        self.game.players[0].sort_hand()
                        self.game.cur = 0
                        self._set_message(f'吃 {self.last_discard} ✓')
                        self.state = 'player_discard'
                        self._build_discard_only_buttons()
                    else:
                        self._set_message('手牌中没有这两张牌，重新选择')
                        self.chi_selected = []

    def _handle_button(self, tag):
        p = self.game.players[0]

        if tag == 'sort':
            p.sort_hand()
            self.selected_card = None

        elif tag == 'query':
            self._show_query_overlay()

        elif self.state == 'player_turn':
            if tag == 'hu':
                if p.can_hu():
                    self._end_game('玩家0 自摸胡牌！', winner=0)
                else:
                    self._set_message('胡牌失败')

            elif tag == 'gang0':
                for c in set(p.hand):
                    if p.gang0(c):
                        p.sort_hand()
                        self._set_message(f'暗杠 {c}')
                        # 再摸一张
                        card = self.game.draw()
                        if card:
                            p.draw(card); p.sort_hand()
                            self.drawn_card = card
                            self._set_message(f'暗杠 {c}，摸到 {card}')
                        self._build_player_buttons()
                        break

            elif tag == 'gang2':
                for c in set(p.hand):
                    if p.gang2(c):
                        p.sort_hand()
                        self._set_message(f'补杠 {c}')
                        # 检查抢杠胡
                        for i in range(1, 4):
                            if self.game.players[i].can_hu_with(c):
                                self._end_game(f'玩家{i} 抢杠胡！', winner=i)
                                return
                        card = self.game.draw()
                        if card:
                            p.draw(card); p.sort_hand()
                            self.drawn_card = card
                        self._build_player_buttons()
                        break

        elif self.state == 'response':
            card = self.last_discard
            if tag == 'hu':
                if p.can_hu_with(card):
                    self._end_game(f'玩家0 点炮胡牌！', winner=0)
                else:
                    self._set_message('胡牌失败')

            elif tag == 'chi':
                # 进入吃牌选牌模式
                self.state = 'chi_select'
                self.chi_selected = []
                self._set_message(f'请从手牌中选2张与【{card}】组成顺子')
                self.buttons = []

            elif tag == 'peng':
                if p.peng(card):
                    p.sort_hand()
                    self._set_message(f'碰 {card}')
                    self.game.cur = 0
                    self.state = 'player_discard'
                    self._build_discard_only_buttons()
                else:
                    self._set_message('碰牌失败')

            elif tag == 'gang1':
                if p.gang1(card):
                    p.sort_hand()
                    self._set_message(f'杠 {card}')
                    self.game.cur = 0
                    card2 = self.game.draw()
                    if card2:
                        p.draw(card2); p.sort_hand()
                        self.drawn_card = card2
                    self.state = 'player_turn'
                    self._build_player_buttons()
                else:
                    self._set_message('杠牌失败')

            elif tag == 'pass':
                self.response_queue.pop(0)
                self._process_response_queue()

        elif self.state == 'player_discard':
            if tag == 'sort':
                p.sort_hand()

    def _build_discard_only_buttons(self):
        """吃/碰后只能出牌状态"""
        self.selected_card = None
        bw, bh = 110, 38
        btn = Button((W//2 - bw//2, 735, bw, bh), '点击手牌出牌', C_BTN_NORM, False)
        btn.tag = 'info'
        sort_btn = Button((W//2 + 70, 735, 90, bh), '理牌 (R)', C_BTN_NORM, True)
        sort_btn.tag = 'sort'
        self.buttons = [btn, sort_btn]

    def _player_discard(self, card):
        p = self.game.players[0]
        p.discard(card)
        self.selected_card = None
        self._set_message(f'打出 {card}')
        self._start_response_phase(card, 0)

    def _handle_key(self, key):
        p = self.game.players[0]
        if key == pygame.K_r:
            p.sort_hand(); self.selected_card = None
        if self.state == 'player_turn':
            if key == pygame.K_h and p.can_hu():
                self._end_game('玩家0 自摸！', winner=0)
        if self.state == 'chi_select' and key == pygame.K_ESCAPE:
            self.state = 'response'
            self.chi_selected = []
            is_next = (0 == (self.discarder + 1) % 4)
            self._build_response_buttons(can_chi=is_next)
            self._set_message('取消吃牌')

    # ──────────────────────── 机器人自动推进 ────────────────────────

    def update(self):
        now = pygame.time.get_ticks()

        if self.state == 'robot_turn':
            if now - self.robot_timer > 900:
                robot = self.game.players[self.game.cur]
                result = robot.auto_move()
                action, card = result

                if action == 'discard':
                    self._set_message(f'玩家{self.game.cur} 打出 {card}')
                    self._start_response_phase(card, self.game.cur)
                elif action == 'gang0':
                    self._set_message(f'玩家{self.game.cur} 暗杠 {card}')
                    new_card = self.game.draw()
                    if new_card: robot.draw(new_card)
                    self.robot_timer = now  # 再等一轮
                elif action == 'gang2':
                    self._set_message(f'玩家{self.game.cur} 补杠 {card}')
                    # 检查玩家0抢杠胡
                    if self.game.players[0].can_hu_with(card):
                        self.state = 'response'
                        self.last_discard = card
                        self.discarder = self.game.cur
                        self._build_response_buttons(can_chi=False)
                        return
                    new_card = self.game.draw()
                    if new_card: robot.draw(new_card)
                    self.robot_timer = now

                # 检查机器人自摸
                if self.game.players[self.game.cur].can_hu():
                    self._end_game(f'玩家{self.game.cur} 自摸！', winner=self.game.cur)

        if self.message_timer and now > self.message_timer:
            if self.state not in ('response','chi_select','game_over'):
                self.message = ''
            self.message_timer = 0

    # ──────────────────────── 辅助 ────────────────────────

    def _set_message(self, msg, duration=2500):
        self.message = msg
        self.message_timer = pygame.time.get_ticks() + duration

    def _end_game(self, msg, winner=-1):
        self.state = 'game_over'
        self.game_over_msg = msg
        self.winning_player = winner
        self.buttons = []

    def _get_card_at(self, pos, hand, start_x, start_y, spacing=TW+4, w=TW, h=TH):
        for i, card in enumerate(hand):
            rect = pygame.Rect(start_x + i*spacing, start_y, w, h)
            if rect.collidepoint(pos):
                return card, i
        return None, -1

    def _hand_pos(self, pid):
        """返回各玩家手牌起始坐标"""
        if pid == 0:
            n = len(self.game.players[0].hand)
            total = n * (TW+4)
            return (W//2 - total//2, 645)
        elif pid == 1:
            return (W - 90, 200)
        elif pid == 2:
            n = len(self.game.players[2].hand)
            total = n * (BTW+3)
            return (W//2 - total//2, 30)
        else:
            return (30, 200)

    def _show_query_overlay(self):
        # 简单显示弃牌信息（覆盖层）
        pass  # 可扩展为完整的查询界面

    # ══════════════════════════════════════════════
    #  绘制
    # ══════════════════════════════════════════════

    def draw(self):
        self._draw_background()
        self._draw_center_info()
        self._draw_discard_areas()
        self._draw_all_hands()
        self._draw_buttons()
        self._draw_message()
        self._draw_player_labels()
        if self.state == 'game_over':
            self._draw_game_over()
        pygame.display.flip()

    def _draw_background(self):
        self.screen.fill(C_BG)
        # 桌布网格纹理
        for x in range(0, W, 60):
            pygame.draw.line(self.screen, C_FELT, (x, 0), (x, H), 1)
        for y in range(0, H, 60):
            pygame.draw.line(self.screen, C_FELT, (0, y), (W, y), 1)
        # 中央桌面
        table = pygame.Rect(160, 140, W-320, H-310)
        pygame.draw.rect(self.screen, C_FELT, table, border_radius=20)
        pygame.draw.rect(self.screen, C_BORDER, table, 3, border_radius=20)

    def _draw_center_info(self):
        # 中央区域：最新弃牌
        cx, cy = W//2, H//2 - 20
        # 剩余牌数
        rem_txt = self.font_md.render(f'剩余 {self.game.remaining()} 张', True, C_TEXT_GOLD)
        self.screen.blit(rem_txt, rem_txt.get_rect(center=(cx, cy - 60)))

        # 最新弃牌
        if self.last_discard:
            label = self.font_sm.render('最新弃牌', True, C_TEXT_LITE)
            self.screen.blit(label, label.get_rect(center=(cx, cy - 20)))
            draw_tile(self.screen, self.last_discard, cx - TW//2, cy, TW, TH)
            # 谁打的
            who = self.font_sm.render(f'玩家{self.discarder}打出', True, C_TEXT_LITE)
            self.screen.blit(who, who.get_rect(center=(cx, cy + TH + 10)))

        # 当前回合指示
        state_map = {
            'player_turn': '你的回合',
            'robot_turn': f'玩家{self.game.cur} 思考中...',
            'response': f'是否响应【{self.last_discard}】？',
            'chi_select': f'选牌吃【{self.last_discard}】（已选{len(self.chi_selected)}张，需选2张）',
            'player_discard': '请选择打出的牌',
            'game_over': '游戏结束',
        }
        cur_state = state_map.get(self.state, '')
        if cur_state:
            st = self.font_md.render(cur_state, True, C_TEXT_GOLD)
            pygame.draw.rect(self.screen, C_PANEL,
                (cx - st.get_width()//2 - 12, cy + TH + 30, st.get_width()+24, 34), border_radius=8)
            self.screen.blit(st, st.get_rect(center=(cx, cy + TH + 47)))

    def _draw_discard_areas(self):
        """四个方向的弃牌区"""
        configs = [
            (self.game.players[0].discard_pile, 280, 570, 'h'),   # 下
            (self.game.players[1].discard_pile, W-170, 300, 'v'), # 右
            (self.game.players[2].discard_pile, 280, 140, 'h'),   # 上
            (self.game.players[3].discard_pile, 170, 300, 'v'),   # 左
        ]
        for pile, sx, sy, direction in configs:
            for i, card in enumerate(pile[-12:]):
                if direction == 'h':
                    draw_tile(self.screen, card, sx + i*(STW+2), sy, STW, STH)
                else:
                    draw_tile(self.screen, card, sx, sy + i*(STH+2), STW, STH)

    def _draw_all_hands(self):
        self._draw_player0_hand()
        for pid in [1, 2, 3]:
            self._draw_robot_hand(pid)

    def _draw_player0_hand(self):
        p = self.game.players[0]
        sx, sy = self._hand_pos(0)
        mouse = pygame.mouse.get_pos()
        for i, card in enumerate(p.hand):
            x = sx + i*(TW+4)
            selected = (card == self.selected_card)
            in_chi = (card in self.chi_selected)
            hover = pygame.Rect(x, sy, TW, TH).collidepoint(mouse)
            offset_y = -14 if (selected or in_chi) else (-6 if hover else 0)
            draw_tile(self.screen, card, x, sy + offset_y, TW, TH,
                      selected=selected or in_chi, hover=hover and not selected)

        # 副露
        sub_x = sx + len(p.hand)*(TW+4) + 16
        for group in p.sub_hand:
            draw_tile_group(self.screen, group, sub_x, sy, STW, STH)
            sub_x += len(group)*(STW+2) + 10

    def _draw_robot_hand(self, pid):
        p = self.game.players[pid]
        n = len(p.hand)

        if pid == 2:  # 上方横排
            sx, sy = self._hand_pos(2)
            for i in range(n):
                draw_tile(self.screen, None, sx + i*(BTW+3), sy, BTW, BTH, face_up=False)
            # 副露
            sub_x = sx - 10
            for group in p.sub_hand:
                sub_x -= len(group)*(STW+2) + 8
                draw_tile_group(self.screen, group, sub_x, sy, STW, STH)

        elif pid == 1:  # 右侧竖排
            sx, sy = self._hand_pos(1)
            for i in range(n):
                draw_tile(self.screen, None, sx, sy + i*(BTH+3), BTH, BTW, face_up=False)

        elif pid == 3:  # 左侧竖排
            sx, sy = self._hand_pos(3)
            for i in range(n):
                draw_tile(self.screen, None, sx, sy + i*(BTH+3), BTH, BTW, face_up=False)

    def _draw_buttons(self):
        for btn in self.buttons:
            btn.draw(self.screen, self.font_btn)

    def _draw_message(self):
        if self.message:
            txt = self.font_md.render(self.message, True, C_TEXT_GOLD)
            bx = W//2 - txt.get_width()//2 - 14
            pygame.draw.rect(self.screen, (0,0,0,160),
                (bx, 700, txt.get_width()+28, 30), border_radius=8)
            self.screen.blit(txt, (bx+14, 703))

    def _draw_player_labels(self):
        labels = ['玩家0（你）', '玩家1', '玩家2', '玩家3']
        positions = [(W//2, H-28), (W-55, H//2), (W//2, 18), (55, H//2)]
        for lbl, (lx, ly) in zip(labels, positions):
            # 当前回合高亮
            is_cur = (
                (lbl == '玩家0（你）' and self.state in ('player_turn','response','chi_select','player_discard')) or
                (self.state == 'robot_turn' and f'玩家{self.game.cur}' in lbl)
            )
            color = C_TEXT_GOLD if is_cur else C_TEXT_LITE
            t = self.font_sm.render(lbl, True, color)
            self.screen.blit(t, t.get_rect(center=(lx, ly)))
            # 手牌数量
            pid = labels.index(lbl)
            cnt = self.font_sm.render(f'({len(self.game.players[pid].hand)}张)', True, (150,160,140))
            self.screen.blit(cnt, cnt.get_rect(center=(lx, ly+16)))

    def _draw_game_over(self):
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # 主标题
        title = self.font_xl.render('游戏结束', True, C_TEXT_GOLD)
        self.screen.blit(title, title.get_rect(center=(W//2, H//2 - 60)))

        msg = self.font_lg.render(self.game_over_msg, True, C_TEXT_LITE)
        self.screen.blit(msg, msg.get_rect(center=(W//2, H//2 + 10)))

        hint = self.font_md.render('按 R 重新开始  /  按 ESC 退出', True, (150,160,140))
        self.screen.blit(hint, hint.get_rect(center=(W//2, H//2 + 70)))

        # 胜者手牌展示
        if self.winning_player >= 0:
            wp = self.game.players[self.winning_player]
            tx = W//2 - (len(wp.hand)*(TW+4))//2
            ty = H//2 + 110
            for i, card in enumerate(wp.hand):
                draw_tile(self.screen, card, tx + i*(TW+4), ty, TW, TH)

    # ──────────────────────── 主循环 ────────────────────────

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                self.handle_event(event)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == 'game_over':
                            pygame.quit(); sys.exit()
                    if event.key == pygame.K_r and self.state == 'game_over':
                        self.__init__()

            self.update()
            self.draw()
            clock.tick(60)


# ══════════════════════════════════════════════
#  入口
# ══════════════════════════════════════════════

if __name__ == '__main__':
    MahjongGUI().run()