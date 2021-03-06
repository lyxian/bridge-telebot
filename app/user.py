from abc import ABC, abstractmethod
from random import sample
from card import Bid, Card, Deck, Rank, Suit
from utils import getToken, createMarkupHand, MongoDb, loadConfig
import requests
import pendulum

def callTelegramAPI(method, params):
    url = 'https://api.telegram.org/bot{}/{}'.format(getToken(), method)
    response = requests.post(url=url, params=params)
    return response.json()

class Game():

    def __init__(self, players, deck, chatId):
        self.deck = deck
        self.players = players
        self.currentBid = None
        self.currentBidder = None
        self.biddingTeam = None
        self.otherTeam = None
        self.brokeTrump = False
        self.roundCount = 0
        self.chatId = chatId
        # self.saveGame

    @property
    def _results(self):
        return ', '.join([f'{player.name}: {player.tricks}' for player in self.players])

    @property
    def _playerResults(self):
        if self.currentBidder:
            return f'{self.currentBid}-{self.currentBidder.likelyPartner} Round {self.roundCount+1}: ' + ' | '.join([f'*{player.name}*: {player.tricks}' if player == self.currentBidder else f'{player.name}: {player.tricks}' for player in self.players])
        else:
            return f'{self.currentBid}-None Round {self.roundCount+1}: ' + ' | '.join([f'*{player.name}*: {player.tricks}' if player == self.currentBidder else f'{player.name}: {player.tricks}' for player in self.players])

    @property
    def _teamResults(self):
        requiredBidTricks = 6 + self.currentBid.number
        biddingTeamScore = sum([i.tricks for i in self.biddingTeam])
        otherTeamScore = sum([i.tricks for i in self.otherTeam])
        biddingTeamMembers = ', '.join([i.name for i in self.biddingTeam])
        otherTeamMembers = ', '.join([i.name for i in self.otherTeam])
        if biddingTeamScore >= requiredBidTricks:
            biddingTeamScore = f'{biddingTeamScore} (WON ≥{requiredBidTricks} tricks)'
        else:
            otherTeamScore = f'{otherTeamScore} (WON ≥{14-requiredBidTricks} tricks)'
        return f'Bidding Team ({biddingTeamMembers}): {biddingTeamScore}\nOther Team ({otherTeamMembers}): {otherTeamScore}'

    @property
    def _randomPlayer(self):
        return sample(self.players, k=1)[0]

    @property
    def _hasEnded(self):
        requiredBidTricks = 6 + self.currentBid.number
        biddingTeamScore = sum([i.tricks for i in self.biddingTeam])
        otherTeamScore = sum([i.tricks for i in self.otherTeam])
        if biddingTeamScore == requiredBidTricks or otherTeamScore == 14 - requiredBidTricks:
            return True
        else:
            return False

    @property
    def _serialize(self):
        # Check if all values 
        return {
            'deck': [_._serialize for _ in self.deck.deck],
            'players': [_._serialize for _ in self.players],
            'currentBid': str(self.currentBid),
            'currentBidder': self.currentBidder.name if self.currentBidder else self.currentBidder,
            'biddingTeam': [_._serialize for _ in self.biddingTeam] if self.biddingTeam else self.biddingTeam,
            'otherTeam': [_._serialize for _ in self.otherTeam] if self.otherTeam else self.otherTeam,
            'brokeTrump': False,
            'roundCount': self.roundCount,
            'chatId': self.chatId,
            'time': pendulum.now().to_datetime_string()
        }

    @property
    def saveGame(self):
        obj = MongoDb(loadConfig())
        payload = self._serialize
        if isinstance(self.chatId, str):
            return
        if obj.has(self.chatId):
            obj.collection.delete_one({'chatId': self.chatId})
            obj.collection.insert_one(payload)
            print(f'Replaced {self.chatId} in DB')
        else:
            obj.collection.insert_one(payload)
            print(f'Added {self.chatId} to DB')
        currSaveId = f'{self.chatId}_curr'
        payload['chatId'] = currSaveId
        payload.pop('_id')
        if obj.has(currSaveId):
            obj.collection.delete_one({'chatId': currSaveId})
            obj.collection.insert_one(payload)
            print(f'Replaced {currSaveId} to DB')
        else:
            obj.collection.insert_one(payload)
            print(f'Added {currSaveId} to DB')


    @property
    def saveGameBackup(self):
        obj = MongoDb(loadConfig())
        saveId = f'{self.chatId}_save'
        if obj.has(self.chatId):
            payload = obj.collection.find_one({'chatId': self.chatId})
            payload.pop('_id')
        else:
            payload = self._serialize
            payload['roundCount'] = payload['roundCount'] - 1
        payload['chatId'] = saveId
        if obj.has(saveId):
            obj.collection.delete_one({'chatId': saveId})
            obj.collection.insert_one(payload)
            print(f'Replaced {saveId} in DB')
        else:
            obj.collection.insert_one(payload)
            print(f'Added {saveId} to DB')

    @property
    def rmSaveGame(self):
        obj = MongoDb(loadConfig())
        if isinstance(self.chatId, str): # do not delete *_curr, *_save
            return
        if obj.has(self.chatId):
            obj.collection.delete_one({'chatId': self.chatId})
            print(f'Removed {self.chatId} in DB')

    @staticmethod
    def hasSaveGame(chatId):
        obj = MongoDb(loadConfig())
        return obj.has(chatId)

    @staticmethod
    def loadGame(payload):
        pass

    def getPlayerOrder(self, firstPlayer):
        playersArray = self.players + self.players[:-1]
        idx = playersArray.index(firstPlayer)
        return playersArray[idx:idx+4]

    def askPlayer(self, winningBidder):
        if isinstance(winningBidder, Player):
            print(f'Your Hand: {Deck.showBySuitStr(winningBidder.hand)}')
            rank, suit = input('Enter partner (eg. "ace spade"): ').split()
            winningBidder.setLikelyPartner([card for card in self.deck.deck if card.rank == rank and card.suit == suit][0])
            return
        else:
            return

    def setTeams(self):
        self.currentBidder.likelyPartner.owner.partner = self.currentBidder # Partner Info
        self.biddingTeam = [self.currentBidder, self.currentBidder.likelyPartner.owner]
        self.otherTeam = [i for i in self.players if i not in self.biddingTeam]

    def setTrump(self, trump=None):
        self.trump = trump

    def setRoundSuit(self, roundCount, suit=None):
        self.roundCount = roundCount
        self.roundSuit = suit

    def setRoundMessageId(self, messageId):
        self.roundMessageId = messageId

    def resetRoundCards(self):
        self.playedCards = []

    def addRoundCards(self, card):
        if not self.brokeTrump and card.isTrump:
            print('***Trump Broke***')
            self.brokeTrump = True
        self.playedCards.append(card)

    def startBidding(self):
        pass

class PlayerBase(ABC):
    
    def __init__(self, name, cards=[]):
        self.name = name
        self.hand = cards
        self.partner = None
        self.likelyPartner = None
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

    @property
    def _serialize(self):
        cardTypes = ['hand', 'availableCards']
        return {
            k: ((v.name if v else v) if k == 'partner' else str(v).strip() if k == 'likelyPartner' else [i._serialize for i in v] if k in cardTypes else v)
            for k,v in vars(self).items()
        }

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

    @staticmethod
    def loadPlayer(payload):
        name = payload['name']
        if name == 'YOU':
            player = Player(name, [])
        else:
            player = Bot(name, [])
        player.hand = [Card.loadCard(card, player) for card in payload['hand']]
        player.tricks = payload['tricks']
        player.partner = payload['partner']
        player.likelyPartner = payload['likelyPartner']
        return player

class Bot(PlayerBase):
    
    def __init__(self, name, cards=[]):
        super().__init__(name, cards)

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
        maxBid = bidStrength // 4 + wildBid
        minBid = 1
        self.likelyPartner = likelyPartner
        if game.currentBid is None:
            return Bid(minBid, bestSuit)
        else:
            if Bid(maxBid, bestSuit) < game.currentBid or game.currentBid.suit == bestSuit:
                return 'Pass'
            else:
                bidObj = Bid(minBid, bestSuit)
                while bidObj <= game.currentBid:
                    minBid += 1
                    bidObj = Bid(minBid, bestSuit)
                return bidObj

    def play(self, game):

        # Possible actions
        # - play highest
        # - play min. highest
        # - play lowest (lose)
        # - play lowest from least suit
        # - play lowest trump (win)
        if self.canFollow(game):
            self.availableCards = [_ for _ in self.hand if _.suit == game.roundSuit]
        else:   
            if not Deck.checkAllTrump(self, game.trump) and (game.roundCount == 0 or (not game.brokeTrump and not game.playedCards)):
                # print('No trump allowed')
                if [_ for _ in self.hand if _.suit == game.trump] == self.hand:
                    self.availableCards = self.hand
                else:
                    self.availableCards = [_ for _ in self.hand if _.suit != game.trump]
            else:
                self.availableCards = self.hand

        if game.playedCards:
            highestCard = sorted(game.playedCards, reverse=True)[0]
            playedCardOwners = [card.owner for card in game.playedCards]
            if self.partner == highestCard.owner:
                cardPlayed = Deck.getLowestCard(self.availableCards)
                return self.hand.pop(self._handIndex[str(cardPlayed).strip()])
            # print(self.name, Deck.getHigherCard(highestCard, self.availableCards), [str(i) for i in self.availableCards])
            cardPlayed = Deck.getHigherCard(highestCard, self.availableCards)
            if cardPlayed:
                return self.hand.pop(self._handIndex[str(cardPlayed).strip()])
            else:
                cardPlayed = Deck.getLowestCard(self.availableCards)
                return self.hand.pop(self._handIndex[str(cardPlayed).strip()])
        else:
            try:
                cardPlayed = Deck.getLowestCard(self.availableCards)
                return self.hand.pop(self._handIndex[str(cardPlayed).strip()])
            except:
                print(f'***************{self.name} has no card to played***************')

class Player(PlayerBase):
    
    def __init__(self, name, cards=[]):
        super().__init__(name, cards)

    def setLikelyPartner(self, card):
        self.likelyPartner = card

    def bid(self, game):
        method = 'sendMessage'
        params = {
            'chat_id': game.chatId,
            'text': 'Your Cards',
            'reply_markup': createMarkupHand(self.hand).to_json()
        }
        print(params)
        print(callTelegramAPI(method, params))
        # self.bot.send_message(game.chatId, 'Your Cards', reply_markup=createMarkupHand(self.hand))

    def play(self, game): # DEPRECIATED
        if self.canFollow(game):
            self.availableCards = [_ for _ in self.hand if _.suit == game.roundSuit]
        else:   
            if game.roundCount == 0 or (not game.brokeTrump and not game.playedCards):
                # print('No trump allowed')
                self.availableCards = [_ for _ in self.hand if _.suit != game.trump]
            else:
                self.availableCards = self.hand
        while True:
            try:
                idx = int(input(f'Enter index of card to be played {self._validIndex}: '))
                if 0 <= idx < len(self.availableCards):
                    break
                else:
                    raise Exception('index beyond hand size')
            except Exception as e:
                print(f'Exception: {e}', end=' | ')
                pass
            print('Error processing input, please try again..')
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