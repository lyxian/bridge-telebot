from abc import ABC, abstractmethod
from card import Rank, Suit, cardMappings
from random import randint, shuffle, sample
from exceptions import IncorrectPlayerCount, InvalidComparison

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

if __name__ == '__main__':

    # ==Game Start==
    deck = Deck()
    deck._shuffle
    # deck._show
    botNames = ['B', 'C', 'D']
    A = Player('YOU')
    B, C, D = [Bot(name) for name in botNames]
    players = [A, B, C, D]

    # ==Bidding==
    game = Game('spade', players)
    deck._setGameRules(game)
    # cards = deck.deck[:13]
    # testing(cards)

    # ==Playing==
    deck.distribute(players)
    firstPlayer = B

    for _ in range(13):
        playerOrder = game.getPlayerOrder(firstPlayer)
        game.setRoundSuit()
        plays = {}

        for player in playerOrder:
            if player == A:
                if game.roundSuit:
                    print(f'Round Suit: {game.roundSuit} || ', end='')
                print('Played Cards: ', end='')
                print(*[f'{player.name}: {card}' for card, player in plays.items()], sep=', ')
            playedCard = player.play(game)
            plays[playedCard] = player
            if game.roundSuit is None:
                game.setRoundSuit(playedCard.suit)
                deck._setRoundRules(game)

        winningCard = sorted(plays.keys())[-1]
        print(*[f'{player.name}: {card}' for card, player in plays.items()], sep=' | ')
        print(f'{plays[winningCard].name} wins with {winningCard}\n')
        firstPlayer = plays[winningCard]
        firstPlayer.tricks += 1
    
    print(f'===Game Ended===\n{game._results}')
