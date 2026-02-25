from player import Player, RobotPlayer
import subprocess
import time
import keyboard
import random


class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

    def __repr__(self):
        return self.suit + self.rank


class Deck:
    def __init__(self):
        self.cards = []
        self._create_deck()
        self.shuffle()

    def _create_deck(self):
        for suit in ['S', 'M', 'P']:
            for rank in '123456789':
                self.cards.extend([suit + rank] * 4)

    def shuffle(self):
        random.shuffle(self.cards)

    def draw_card(self):
        return self.cards.pop() if self.cards else None

    def remaining_cards(self):
        return len(self.cards)


class Mahjong:
    def __init__(self):
        self.players = [Player(0), RobotPlayer(1), RobotPlayer(2), RobotPlayer(3)]
        self.deck = Deck()
        self.current_player_index = 0
        self.cheat = False

    # ──────────────────────────────────────────────
    # 初始化 / 发牌
    # ──────────────────────────────────────────────

    def deal_cards(self):
        for _ in range(13):
            for player in self.players:
                player.draw_card(self.deck.draw_card())

    def user_choose(self, all_hands):
        """用户自定义四家手牌（每家13张）"""
        for i, hand in enumerate(all_hands):
            if len(hand) != 13:
                print(f"  ✗ 玩家 {i} 的牌数不是13张")
                return False
            for card in hand:
                if card in self.deck.cards:
                    self.deck.cards.remove(card)
                    self.players[i].draw_card(card)
                else:
                    print(f"  ✗ 牌 [{card}] 不在牌堆中（已被使用或不存在）")
                    return False
        return True

    # ──────────────────────────────────────────────
    # 查询
    # ──────────────────────────────────────────────

    def querys(self):
        print("\n──── 查询面板 ────")
        while True:
            pid = input("请输入要查询的玩家编号 (0-3)，或输入 [退出] 返回游戏：").strip()
            if pid == '退出':
                break
            if pid not in '0123' or len(pid) != 1:
                print("  无效输入，请输入 0~3 或「退出」")
                continue
            pid = int(pid)
            options = "  [1] 弃牌  [2] 副露"
            if self.cheat:
                options += "  [3] 手牌（作弊模式）"
            choice = input(f"{options}\n  请选择：").strip()
            p = self.players[pid]
            if choice == '1':
                print(f"  玩家 {pid} 弃牌：{' '.join(p.discard_pile) or '（无）'}")
            elif choice == '2':
                print(f"  玩家 {pid} 副露：{p.print_sub_hand() or '（无）'}")
            elif choice == '3' and self.cheat:
                print(f"  玩家 {pid} 手牌：{' '.join(p.hand)}")
            else:
                print("  无效选项")
        print("─────────────────\n")

    # ──────────────────────────────────────────────
    # 核心：结束阶段——所有其他玩家对当前弃牌的响应
    # ──────────────────────────────────────────────

    def every_one_move(self, discarded_card):
        """
        返回值：
          True  → 游戏结束（有人胡牌）
          False → 游戏继续，轮到新的 current_player_index
          None  → 无人响应，轮到下一家（由调用方 next_turn）
        """
        discarder = self.current_player_index
        # 按顺序从下家开始检查
        for k in range(1, 4):
            j = (discarder + k) % 4
            is_next = (j == (discarder + 1) % 4)  # 是否是直接下家（可吃牌）

            if j == 0:
                # 玩家 0 的决策
                result = self.decision(discarded_card, can_chi=is_next)
                if result is True:
                    return True
                elif result is False:
                    return False
                elif isinstance(result, str):
                    # 吃/碰后返回弃牌
                    return self.every_one_move(result)
                # None → 继续检查下一家
            else:
                robot = self.players[j]
                move = robot.make_move_上家_turn(discarded_card) if is_next \
                    else robot.make_move_非上家_turn(discarded_card)

                if move == 0:  # 胡
                    print(f"\n  玩家 {j} 胡！（点炮：玩家 {discarder} 打出 {discarded_card}）")
                    robot.hu_in_other_turn(discarded_card)
                    return True

                elif move in (1, 2):  # 吃 / 碰
                    action = "吃" if move == 1 else "碰"
                    print(f"  玩家 {j} {action}了 玩家 {discarder} 打出的 {discarded_card}")
                    self._pause()
                    self.current_player_index = j
                    card = robot.make_discard_move()
                    print(f"  玩家 {j} 打出：{card}")
                    return self.every_one_move(card)

                elif move == 3:  # 杠
                    print(f"  玩家 {j} 杠了 玩家 {discarder} 打出的 {discarded_card}")
                    self._pause()
                    self.current_player_index = j
                    return False  # 杠后该玩家再摸牌

                # move == 4：跳过

        return None  # 所有人跳过

    # ──────────────────────────────────────────────
    # 玩家 0 在结束阶段的交互
    # ──────────────────────────────────────────────

    def decision(self, discarded_card, can_chi=False):
        """
        返回值：
          True       → 胡牌，游戏结束
          False      → 杠，游戏继续（玩家0再摸牌）
          str (card) → 吃/碰后打出的牌，需继续结束阶段
          None       → 跳过
        """
        actions = "[0]胡  [2]碰  [3]杠  [4]跳过"
        if can_chi:
            actions = "[0]胡  [1]吃  [2]碰  [3]杠  [4]跳过"
        print(f"\n  玩家 {self.current_player_index} 打出了 【{discarded_card}】")
        print(f"  可选操作：{actions}  [7]理牌  [Q]查询")

        while True:
            choice = input("  请选择：").strip()

            if choice == '0':
                if self.players[0].other_run_hu(discarded_card):
                    print(f"\n  ★ 玩家0 胡！（点炮：玩家 {self.current_player_index} 打出 {discarded_card}）")
                    self.players[0].hu_in_other_turn(discarded_card)
                    return True
                print("  胡牌失败，条件不满足")

            elif choice == '1':
                if not can_chi:
                    print("  本轮不能吃牌（只有下家可以吃）")
                    continue
                raw = input("  请输入顺子（三张牌，空格分隔，例：S1 S2 S3）：").strip()
                if raw.upper() == 'Q':
                    self.querys()
                    continue
                chow_set = raw.split()
                if not self.players[0].is_valid_chi(chow_set):
                    print("  无效顺子，请重新输入")
                    continue
                if self.players[0].chi(discarded_card, chow_set):
                    print(f"  玩家0 吃 {discarded_card}，组成 {chow_set}")
                    self.current_player_index = 0
                    card = self._player0_discard()
                    return card
                print("  吃牌失败，手中没有对应的牌")

            elif choice == '2':
                if self.players[0].peng(discarded_card):
                    print(f"  玩家0 碰 {discarded_card}")
                    self.current_player_index = 0
                    card = self._player0_discard()
                    return card
                print("  碰牌失败，手中没有两张相同的牌")

            elif choice == '3':
                if self.players[0].gang1(discarded_card):
                    print(f"  玩家0 杠 {discarded_card}")
                    self.current_player_index = 0
                    return False
                print("  杠牌失败，手中没有三张相同的牌")

            elif choice == '4':
                return None

            elif choice == '7':
                self.players[0].lipai()

            elif choice.upper() == 'Q':
                self.querys()

            else:
                print("  无效输入，请重新选择")

    # ──────────────────────────────────────────────
    # 玩家 0 回合
    # ──────────────────────────────────────────────

    def handle_player_turn(self, current_player):
        print(f"\n{'='*40}")
        print(f"  ▶ 你的回合（玩家0）  剩余牌数：{self.deck.remaining_cards()}")
        card_drawn = self.deck.draw_card()
        if card_drawn is None:
            return self._no_cards_left()

        current_player.draw_card(card_drawn)
        print(f"  摸到：【{card_drawn}】")
        self._show_player0_info()

        while True:
            print("\n  操作：[0]胡  [1]切牌  [4]暗杠  [6]补杠  [7]理牌  [8]切摸到的牌  [Q]查询")
            choice = input("  请选择：").strip()

            if choice == '0':
                if current_player.hu():
                    print(f"\n  ★ 玩家0 自摸！")
                    current_player.hu_show_hand()
                    return True
                print("  自摸失败，条件不满足")

            elif choice == '1':
                card = input("  请输入要打出的牌：").strip()
                if card in current_player.hand:
                    self.discard_card(current_player, card)
                    print(f"  玩家0 打出：{card}")
                    result = self.every_one_move(card)
                    if result is True:
                        return True
                    self.next_turn() if result is None else None
                    return False
                elif card.upper() == 'Q':
                    self.querys()
                else:
                    print("  手中没有这张牌")

            elif choice == '4':
                card = input("  请输入要暗杠的牌：").strip()
                if card.upper() == 'Q':
                    self.querys()
                    continue
                if current_player.gang0(card):
                    print(f"  玩家0 暗杠 {card}，再摸一张")
                    return False  # 继续本玩家回合
                print("  暗杠失败，手中不足四张")

            elif choice == '6':
                card = input("  请输入要补杠的牌：").strip()
                if card.upper() == 'Q':
                    self.querys()
                    continue
                if current_player.gang2(card):
                    print(f"  玩家0 补杠 {card}")
                    # 其他玩家可以抢杠胡
                    for i in range(1, 4):
                        if self.players[i].other_run_hu(card):
                            print(f"  玩家 {i} 抢杠胡！")
                            self.players[i].hu_show_hand()
                            return True
                    print("  玩家0 再摸一张")
                    return False
                print("  补杠失败")

            elif choice == '7':
                current_player.lipai()

            elif choice == '8':
                self.discard_card(current_player, card_drawn)
                print(f"  玩家0 打出摸到的牌：{card_drawn}")
                result = self.every_one_move(card_drawn)
                if result is True:
                    return True
                self.next_turn() if result is None else None
                return False

            elif choice.upper() == 'Q':
                self.querys()

            else:
                print("  无效输入，请重新选择")

    def _show_player0_info(self):
        print(f"  ──── 当前手牌 ────")
        self.players[0].show_self_hand()

    # ──────────────────────────────────────────────
    # 机器人回合
    # ──────────────────────────────────────────────

    def handle_robot_turn(self, current_player):
        idx = self.current_player_index
        print(f"\n{'='*40}")
        print(f"  ▶ 玩家 {idx} 的回合  剩余牌数：{self.deck.remaining_cards()}")
        card_drawn = self.deck.draw_card()
        if card_drawn is None:
            return self._no_cards_left()

        current_player.draw_card(card_drawn)
        # 始终显示玩家0手牌
        print("  ──── 你的手牌 ────")
        self.players[0].show_self_hand()

        if current_player.hu_check():
            print(f"\n  ★ 玩家 {idx} 自摸！")
            current_player.hu_show_hand()
            return True

        move = current_player.make_move()
        card, action = move[0], move[1]

        if action == 0:  # 暗杠
            print(f"  玩家 {idx} 暗杠 {card}，再摸一张")
            return False

        elif action == 2:  # 补杠
            print(f"  玩家 {idx} 补杠 {card}")
            # 检查其他玩家（含玩家0）抢杠胡
            for k in range(1, 4):
                j = (idx + k) % 4
                if j != idx:
                    if j == 0:
                        while True:
                            a = input("  有人补杠，选择 [0]无视  [1]抢杠胡：").strip()
                            if a == '0':
                                break
                            elif a == '1':
                                if self.players[0].other_run_hu(card):
                                    print(f"  玩家0 抢杠胡！")
                                    self.players[0].hu_in_other_turn(card)
                                    return True
                                print("  胡牌失败")
                            else:
                                print("  无效输入")
                    else:
                        if self.players[j].other_run_hu(card):
                            print(f"  玩家 {j} 抢杠胡！")
                            self.players[j].hu_show_hand()
                            return True
            print(f"  玩家 {idx} 再摸一张")
            return False

        else:  # 切牌
            print(f"  玩家 {idx} 打出：{card}")
            result = self.every_one_move(card)
            if result is True:
                return True
            self.next_turn() if result is None else None
            return False

    # ──────────────────────────────────────────────
    # 辅助
    # ──────────────────────────────────────────────

    def _player0_discard(self):
        """玩家0选择打出一张牌，返回打出的牌"""
        while True:
            self._show_player0_info()
            card = input("  请选择打出的牌（输入Q查询）：").strip()
            if card.upper() == 'Q':
                self.querys()
            elif card in self.players[0].hand:
                self.discard_card(self.players[0], card)
                print(f"  玩家0 打出：{card}")
                return card
            else:
                print("  手中没有这张牌，请重新输入")

    def _no_cards_left(self):
        print("\n  牌堆已空，本局流局。")
        self.show_all_hands()
        return True

    def _pause(self):
        print("  按 Enter 继续...")
        keyboard.wait('enter')

    def discard_card(self, player, card):
        player.discard_card(card)

    def next_turn(self):
        self.current_player_index = (self.current_player_index + 1) % 4

    def show_all_hands(self):
        for player in self.players:
            player.show_hand()

    # ──────────────────────────────────────────────
    # 欢迎 / 初始化
    # ──────────────────────────────────────────────

    def welcome(self):
        print("\n╔══════════════════════╗")
        print("║      欢迎来玩麻将！      ║")
        print("╚══════════════════════╝")
        print("  牌型说明：S=条  M=万  P=饼  数字1-9")

        while True:
            a = input("\n  是否开始游戏？[yes/no]：").strip().lower()
            if a == 'no':
                print("  好吧，下次再玩！再见~")
                return False
            elif a == 'yes':
                break
            print("  请输入 yes 或 no")

        while True:
            a = input("  发牌方式：[1] 随机发牌  [2] 自定义手牌：").strip()
            if a == '1':
                print("  随机发牌，准备开始！")
                self.deal_cards()
                return True
            elif a == '2':
                print("  请依次输入玩家 0~3 的手牌，每行13张，空格分隔：")
                all_hands = []
                for i in range(4):
                    hand = input(f"  玩家 {i}：").strip().split()
                    all_hands.append(hand)
                if self.user_choose(all_hands):
                    print("  手牌设置成功，准备开始！")
                    return True
                print("  手牌输入有误，请重新输入（注意：每家13张，且牌面合法不重复）")
            else:
                print("  请输入 1 或 2")

    def cheats(self):
        a = input("\n  是否开启作弊模式（可在查询中查看他人手牌）？[yes/no]：").strip().lower()
        if a == 'yes':
            self.cheat = True
            print("  ⚠ 作弊模式已开启")

    # ──────────────────────────────────────────────
    # 主循环
    # ──────────────────────────────────────────────

    def game_loop(self):
        if not self.welcome():
            return
        self.cheats()
        time.sleep(1)
        subprocess.call('cls', shell=True)

        while True:
            current_player = self.players[self.current_player_index]
            if self.current_player_index == 0:
                game_over = self.handle_player_turn(current_player)
            else:
                game_over = self.handle_robot_turn(current_player)

            if game_over:
                print("\n  ══════ 游戏结束 ══════")
                break

            time.sleep(0.8)
            subprocess.call('cls', shell=True)

if __name__ == "__main__":
    game = Mahjong()
    game.game_loop()
