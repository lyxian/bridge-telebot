from exceptions import IncorrectPlayerCount
from random import sample
from enum import Enum

class Rank(Enum):
    two = 1
    three = 2
    four = 3
    five = 4
    six = 5
    seven = 6
    eight = 7
    nine = 8
    ten = 9
    jack = 10
    queen = 11
    king = 12
    ace = 13

class Suit(Enum):
    club = 1
    diamond = 2
    heart = 3
    spade = 4

cardMappings = {
    'ace': 'A',
    'two': '2',
    'three': '3',
    'four': '4',
    'five': '5',
    'six': '6',
    'seven': '7',
    'eight': '8',
    'nine': '9',
    'ten': '10',
    'jack': 'J',
    'queen': 'Q',
    'king': 'K',
    'club': '♣',
    'diamond': '♦',
    'heart': '♥',
    'spade': '♠'
}

class Card:

    def __init__(self, rank, suit):
        self.rank = Rank(rank).name
        self.suit = Suit(suit).name
        self.isTrump = False
        self.isRoundSuit = False

    def __str__(self):
        return '{:>2}{}'.format(cardMappings[self.rank], cardMappings[self.suit])

    def __lt__(self, other):
        if self.suit == other.suit:
            return Rank[self.rank].value < Rank[other.rank].value
        else:
            if self.isTrump and not other.isTrump:
                return False
            elif not self.isTrump and other.isTrump:
                return True
            elif self.isRoundSuit and not other.isRoundSuit:
                return False
            elif not self.isRoundSuit and other.isRoundSuit:
                return True
            else:
                return Suit[self.suit].value < Suit[other.suit].value
                # raise InvalidComparison(self, other)

    # def __gt__(self, other):
    #     return Rank[self.rank].value >= Rank[other.rank].value and Suit[self.suit].value >= Suit[other.suit].value

class Deck:

    def __init__(self):
        self.deck = [Card(i,j) for i in range(1,1+len(Rank._member_names_)) for j in range(1,1+len(Suit._member_names_))]
        
    @property
    def _shuffle(self):
        self.deck = sample(self.deck, k=len(self.deck))

    @property
    def _show(self):
        print([str(i) for i in self.deck])

    def _setGameRules(self, game):
        for card in self.deck:
            card.isTrump = card.suit == game.trump

    def _setRoundRules(self, game):
        for card in self.deck:
            card.isRoundSuit = card.suit == game.roundSuit

    def distribute(self, players):
        if len(players) == 4:
            self._shuffle
            for i in range(4):
                players[i].hand = sorted(self.deck[13*i:13*(i+1)])
            print('Deck distributed.')
        else:
            raise IncorrectPlayerCount