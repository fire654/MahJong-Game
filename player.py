import random
import copy

class Player:
    def __init__(self, player_id):
        self.player_id = player_id
        self.hand = []
        self.sub_hand = []
        self.discard_pile = []

    def draw_card(self, card):
        self.hand.append(card)

    def discard_card(self, card):
        self.hand.remove(card)
        self.discard_pile.append(card)

    def chi(self, card, chow_set):
        if card not in chow_set:
            return False
        others = [c for c in chow_set if c != card]
        if all(c in self.hand for c in others):
            for c in others:
                self.hand.remove(c)
            self.sub_hand.append(chow_set)
            return True
        return False

    def is_valid_chi(self, chow_cards):
        if len(chow_cards) != 3:
            return False
        suits = 'SMP'
        ranks = '123456789'
        cards = [list(c) for c in chow_cards]
        if not all(len(c) == 2 and c[0] in suits and c[1] in ranks for c in cards):
            return False
        if cards[0][0] == cards[1][0] == cards[2][0]:
            r = sorted(int(c[1]) for c in cards)
            return r[1] - r[0] == 1 and r[2] - r[1] == 1
        return False

    def peng(self, card):
        if self.hand.count(card) >= 2:
            self.sub_hand.append([card] * 3)
            self.hand.remove(card)
            self.hand.remove(card)
            return True
        return False

    def gang1(self, card):
        if self.hand.count(card) >= 3:
            self.sub_hand.append([card] * 4)
            for _ in range(3):
                self.hand.remove(card)
            return True
        return False

    def gang0(self, card):
        if self.hand.count(card) >= 4:
            self.sub_hand.append([card] * 4)
            for _ in range(4):
                self.hand.remove(card)
            return True
        return False

    def gang2(self, card):
        if [card] * 3 in self.sub_hand and self.hand.count(card) == 1:
            self.sub_hand.remove([card] * 3)
            self.sub_hand.append([card] * 4)
            self.hand.remove(card)
            self.discard_pile.append(card)
            return True
        return False

    def hu_list(self, a):
        if not a or all(x == 0 for x in a):
            return 1
        i = next((j for j, x in enumerate(a) if x != 0), None)
        if a[i] < 3:
            if len(a) >= i + 3 and a[i+1] != 0 and a[i+2] != 0:
                a[i] -= 1; a[i+1] -= 1; a[i+2] -= 1
                return self.hu_list(a)
            return 0
        else:
            if len(a) >= i + 3 and a[i+1] != 0 and a[i+2] != 0:
                a[i] -= 1
                b = copy.deepcopy(a)
                b[i] -= 2
                a[i+1] -= 1; a[i+2] -= 1
                return max(self.hu_list(a), self.hu_list(b))
            a[i] -= 3
            return self.hu_list(a)

    def is_hu(self, tiles):
        counts = {'S': [0]*9, 'M': [0]*9, 'P': [0]*9}
        for t in tiles:
            counts[t[0]][int(t[1]) - 1] += 1
        for suit in counts:
            for i in range(9):
                if counts[suit][i] >= 2:
                    counts[suit][i] -= 2
                    S, M, P = (copy.deepcopy(counts[s]) for s in 'SMP')
                    if self.hu_list(S) * self.hu_list(M) * self.hu_list(P) == 1:
                        return True
                    counts[suit][i] += 2
        return False

    def other_run_hu(self, card):
        return self.is_hu(self.hand + [card])

    def hu(self):
        return self.is_hu(self.hand)

    def print_sub_hand(self):
        return ''.join(f"({' '.join(p)})" for p in self.sub_hand)

    def show_hand(self):
        print(f"Player {self.player_id} hand: {' '.join(self.hand)}")
        print(f"Player {self.player_id} sub_hand: {self.print_sub_hand()}")

    def show_self_hand(self):
        print(f"Hand: {' '.join(self.hand)}")
        print(f"Sub Hand: {self.print_sub_hand()}")

    def hu_show_hand(self):
        sub = self.print_sub_hand()
        print(f"{' '.join(self.hand)}" + (f"+{sub}" if sub else ""))

    def hu_in_other_turn(self, card):
        sub = self.print_sub_hand()
        print(f"{' '.join(self.hand)}" + (f"+{sub}" if sub else "") + f"+{card}")

    def lipai(self):
        self.hand.sort(key=lambda x: (x[0], int(x[1])))
        print(f"Hand: {' '.join(self.hand)}")


class RobotPlayer(Player):
    def __init__(self, player_id):
        super().__init__(player_id)

    def random_discard(self):
        if self.hand:
            card = random.choice(self.hand)
            self.hand.remove(card)
            self.discard_pile.append(card)
            return card

    def make_move(self):
        for card in set(self.hand):
            if self.gang0(card):
                return [card, 0]
        for card in set(self.hand):
            if self.gang2(card):
                return [card, 2]
        return [self.random_discard(), 1]

    def make_discard_move(self):
        return self.random_discard()

    def _try_chi(self, card):
        for c1 in self.hand:
            for c2 in self.hand:
                for chow in ([c1, c2, card], [c1, card, c2], [c2, c1, card]):
                    if self.is_valid_chi(chow) and self.chi(card, chow):
                        return True
        return False

    def make_move_上家_turn(self, card):
        if self.other_run_hu(card): return 0
        if self._try_chi(card): return 1
        if self.peng(card): return 2
        if self.gang1(card): return 3
        return 4

    def make_move_非上家_turn(self, card):
        if self.other_run_hu(card): return 0
        if self.peng(card): return 2
        if self.gang1(card): return 3
        return 4

    def hu_check(self):
        return self.hu()