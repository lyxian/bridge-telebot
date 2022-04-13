from abc import ABC, abstractmethod
from random import sample
from card import Bid, Card, Deck, Rank, Suit

class Game():

    def __init__(self, players, deck):
        self.deck = deck
        self.players = players
        self.currentBid = None
        self.currentBidder = None
        self.biddingTeam = None
        self.otherTeam = None

    @property
    def _results(self):
        return ', '.join([f'{player.name}: {player.tricks}' for player in self.players])

    @property
    def _teamResults(self):
        requiredBidTricks = 6 + self.currentBid.number
        biddingTeamScore = sum([i.tricks for i in self.biddingTeam])
        otherTeamScore = sum([i.tricks for i in self.otherTeam])
        biddingTeamMembers = ', '.join([i.name for i in self.biddingTeam])
        otherTeamMembers = ', '.join([i.name for i in self.otherTeam])
        if biddingTeamScore > requiredBidTricks:
            biddingTeamScore = f'{biddingTeamScore} (WON at least {requiredBidTricks} tricks)'
        else:
            otherTeamScore = f'{otherTeamScore} (WON at least {14-requiredBidTricks} tricks)'
        return f'Bidding Team ({biddingTeamMembers}): {biddingTeamScore}\nOther Team ({otherTeamMembers}): {otherTeamScore}'

    @property
    def _randomPlayer(self):
        return sample(self.players, k=1)[0]

    def getPlayerOrder(self, firstPlayer):
        playersArray = self.players + self.players[:-1]
        idx = playersArray.index(firstPlayer)
        return playersArray[idx:idx+4]

    def askPlayer(self, winningBidder):
        if isinstance(winningBidder, Player):
            rank, suit = input('Enter partner (eg. "ace spade"): ').split()
            winningBidder.likelyPartner = Card(rank, suit)
            return
        else:
            return

    def setTeams(self):
        self.biddingTeam = [self.currentBidder, self.currentBidder.likelyPartner.owner]
        self.otherTeam = [i for i in self.players if i not in self.biddingTeam]

    def setTrump(self, trump=None):
        self.trump = trump

    def setRoundSuit(self, suit=None):
        self.roundSuit = suit

    def startBidding(self):
        pass

class PlayerBase(ABC):
    
    def __init__(self, name, cards=[]):
        self.name = name
        self.hand = cards
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

    @property
    def _handStrength(self):
        return Deck.showStrength(self.hand)

    def getBestSuit(self, num=0):
        return sorted(Deck.showSuitStrength(self.hand).items(), key=lambda x: x[1], reverse=True)[num][0]

    def canFollow(self, game):
        self.hand = sorted(self.hand)
        return len([_ for _ in self.hand if _.suit == game.roundSuit]) != 0

    @abstractmethod
    def bid(self, game):
        pass

    @abstractmethod
    def play(self, game):
        return

class Bot(PlayerBase):
    
    def __init__(self, name, cards=[]):
        super().__init__(name, cards)
        self.knowPartner = False

    def bid(self, game):
        handBySuit = Deck.showBySuit(self.hand)
        for i in range(5):
            if i == 4:
                bestSuit = self.getBestSuit(0)
                break
            bestSuit = self.getBestSuit(i)
            if len(handBySuit[bestSuit]) >= 4 and Deck.showStrength(handBySuit[bestSuit]) > 1:
                break
        likelyPartner = Deck.showLikelyPartner(handBySuit[bestSuit], game.deck)
        print(Deck.showBySuitStr(self.hand), bestSuit, Deck.showStrength(handBySuit[bestSuit]), likelyPartner)
        strengthIncrease = 1 + likelyPartner.strength
        bidStrength = Deck.showStrength(handBySuit[bestSuit]) + strengthIncrease

        wildBid = bidStrength % 4 >= sample(range(1,5), k=1)[0]
        minBid = bidStrength // 4 + wildBid

        bidObj = Bid(minBid, bestSuit)
        self.likelyPartner = likelyPartner
        if game.currentBid is None or game.currentBid < bidObj:
            return bidObj
        else:
            return 'pass'

    def play(self, game):
        if self.canFollow(game):
            self.availableCards = [_ for _ in self.hand if _.suit == game.roundSuit]
        else:
            self.availableCards = self.hand
        cardPlayed = str(sample(self.availableCards, k=1)[0]).strip()
        return self.hand.pop(self._handIndex[cardPlayed])

    def think(self, game):
        pass

class Player(PlayerBase):
    
    def __init__(self, name, cards=[]):
        super().__init__(name, cards)

    def bid(self, game):
        print(Deck.showBySuitStr(self.hand))
        minBid = input('Enter min. bid: ')
        if minBid == 'pass':
            return minBid
        bestSuit = input('Enter suit: ')
        if bestSuit == 'pass':
            return bestSuit
        bidObj = Bid(int(minBid), bestSuit)
        if game.currentBid is None or game.currentBid < bidObj:
            return bidObj
        else:
            return 'pass'

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