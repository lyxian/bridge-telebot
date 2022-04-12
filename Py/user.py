from abc import ABC, abstractmethod
from random import sample

class Game():

    def __init__(self, trump, players):
        self.trump = trump
        self.players = players

    def getPlayerOrder(self, firstPlayer):
        playersArray = self.players + self.players[:-1]
        idx = playersArray.index(firstPlayer)
        return playersArray[idx:idx+4]

    def setRoundSuit(self, suit=None):
        self.roundSuit = suit

    @property
    def _results(self):
        return ', '.join([f'{player.name}: {player.tricks}' for player in self.players])

class PlayerBase(ABC):
    
    def __init__(self, name, cards=[]):
        self.name = name
        self.hand = cards
        self.handScore = 0
        self.partner = None
        self.tricks = 0
        self.availableCards = cards

    @property
    def _show(self):
        print([str(i) for i in self.hand])

    @property
    def _handIndex(self):
        return {str(val).strip(): idx for idx, val in enumerate(self.hand)}

    @property
    def _validIndex(self):
        return {str(val).strip(): idx for idx, val in enumerate(sorted(self.availableCards))}

    def canFollow(self, game):
        self.hand = sorted(self.hand)
        return len([_ for _ in self.hand if _.suit == game.roundSuit]) != 0

    @abstractmethod
    def play(self):
        return

class Bot(PlayerBase):
    
    def __init__(self, name, cards=[]):
        super().__init__(name, cards)

    def play(self, game):
        if self.canFollow(game):
            self.availableCards = [_ for _ in self.hand if _.suit == game.roundSuit]
        else:
            self.availableCards = self.hand
        cardPlayed = str(sample(self.availableCards, k=1)[0]).strip()
        return self.hand.pop(self._handIndex[cardPlayed])

class Player(PlayerBase):
    
    def __init__(self, name, cards=[]):
        super().__init__(name, cards)

    def play(self, game):
        if self.canFollow(game):
            self.availableCards = [_ for _ in self.hand if _.suit == game.roundSuit]
        else:
            self.availableCards = self.hand
        idx = int(input(f'Enter index of card to be played {self._validIndex}: '))
        cardPlayed = str(self.availableCards[idx]).strip()
        return self.hand.pop(self._handIndex[cardPlayed])


def testing(cards):
    if 0:
        for _ in cards:
            print(str(_), vars(_))
    
    if 0:
        from itertools import combinations
        for pair in combinations(range(7), 2):
            a, b = [cards[i] for i in pair]
            print(f'{a} < {b} : {a<b}')

    print([str(i) for i in sorted(cards)])