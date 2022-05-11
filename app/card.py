from exceptions import IncorrectPlayerCount, CannotFindLikelyPartner, ImprobableHand
from collections import Counter
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
    notrump = 5

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
    'A': 'ace',
    '2': 'two',
    '3': 'three',
    '4': 'four',
    '5': 'five',
    '6': 'six',
    '7': 'seven',
    '8': 'eight',
    '9': 'nine',
    '10': 'ten',
    'J': 'jack',
    'Q': 'queen',
    'K': 'king',
    'club': '♣',
    'diamond': '♦',
    'heart': '♥',
    'spade': '♠',
    'notrump': 'NT',
    '♣': 'club',
    '♦': 'diamond',
    '♥': 'heart',
    '♠': 'spade',
    'NT': 'notrump'
}

cardStrength = {
    'jack': 1,
    'queen': 2,
    'king': 3,
    'ace': 4,
}

class Bid:

    def __init__(self, number, suit):
        self.number = number
        self.suit = suit

    def __str__(self):
        return '{}{}'.format(self.number, cardMappings[self.suit])

    def __lt__(self, other):
        if self.number == other.number:
            return Suit[self.suit].value < Suit[other.suit].value
        else:
            return self.number < other.number

    def __le__(self, other):
        if self.number == other.number:
            return Suit[self.suit].value <= Suit[other.suit].value
        else:
            return self.number <= other.number

class Card:

    def __init__(self, rank, suit):
        if isinstance(rank, int):
            self.rank = Rank(rank).name
        else:
            self.rank = rank
        if isinstance(suit, int):
            self.suit = Suit(suit).name
        else:
            self.suit = suit
        self.isTrump = False
        self.isRoundSuit = False
        self.strength = cardStrength.get(self.rank, 0)
        self.owner = None

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
                
    @property
    def _serialize(self):
        return {k:(v.name if 'user' in str(type(v)) else v) for k,v in vars(self).items()}

    @staticmethod
    def loadCard(payload, owner):
        card = Card(payload['rank'], payload['suit'])
        card.isTrump = payload['isTrump']
        card.isRoundSuit = payload['isRoundSuit']
        card.owner = owner
        return card

class Deck:

    def __init__(self):
        self.deck = [Card(i,j) for i in range(1,1+len(Rank._member_names_)) for j in range(1,len(Suit._member_names_))]
        
    @property
    def _shuffle(self):
        self.deck = sample(self.deck, k=len(self.deck))

    @property
    def _show(self):
        print([str(i) for i in self.deck])

    def _setGameRules(self, game):
        for card in self.deck:
            card.isTrump = card.suit == game.trump
        game.setTeams()

    def _setRoundRules(self, game):
        for card in self.deck:
            card.isRoundSuit = card.suit == game.roundSuit

    def distribute(self, players):
        if len(players) == 4:
            self._shuffle
            for i in range(4):
                players[i].hand = sorted(self.deck[13*i:13*(i+1)])
                for card in players[i].hand:
                    card.owner = players[i]
            print('Deck distributed.')
        else:
            raise IncorrectPlayerCount

    @staticmethod
    def showBySuit(cards):
        suits = Suit._member_names_[:4]
        return {suit: [card for card in cards if card.suit == suit][::-1] for suit in suits}

    @staticmethod
    def showBySuitStr(cards):
        suits = Suit._member_names_[:4]
        return {suit: [str(card) for card in cards if card.suit == suit] for suit in suits}

    @staticmethod
    def showStrength(cards):
        return sum([i.strength for i in cards]) + \
            sum(map(lambda x: x-4 if x>4 else 0, Counter([i.suit for i in cards]).values()))

    @staticmethod
    def showSuitStrength(cards):
        suits = Suit._member_names_[:4]
        return {suit: Deck.showStrength([card for card in cards if card.suit == suit]) for suit in suits}

    @staticmethod
    def showLikelyPartner(cards, deck):
        suit = cards[0].suit
        for card in cards:
            if card.suit != suit:
                raise CannotFindLikelyPartner
        ranks = [card.rank for card in cards]
        for rank in Rank._member_names_[::-1]:
            if rank not in ranks:
                return [card for card in deck.deck if card.rank == rank and card.suit == suit][0]
        raise ImprobableHand

    @staticmethod
    def getHigherCard(card, cards):
        _ = cards.copy(); _.append(card); _ = sorted(_)
        higherCardIndex = _.index(card)
        if higherCardIndex < len(cards):
            return cards[higherCardIndex]
        else:
            return None

    @staticmethod
    def getLowestCard(cards):
        return sorted(cards)[0]

    @staticmethod
    def findCard(cards, suit, rank):
        for card in cards:
            if card.suit == suit and card.rank == rank:
                return card
        return None

if __name__ == '__main__':
    pass