from cryptography.fernet import Fernet
import pymongo
import yaml
import os

def loadConfig():
    try:
        with open('config.yaml', 'r') as stream:
            yamlData = yaml.safe_load(stream)
        return yamlData
    except Exception as e:
        print(e)
        return ''

# Manage subscribers
class MongoDb:
    def __init__(self, configData):
        self.collection = self.connect(configData)

    def connect(self, configData):
        key = bytes(os.getenv("KEY"), "utf-8")
        password = Fernet(key).decrypt(bytes(os.getenv("SECRET_MONGODB"), "utf-8")).decode()
        databaseConfig = configData['application']['database']
        databaseConfig = {
            'host': os.getenv('HOST'),
            'password': password, **databaseConfig}
        connection = pymongo.MongoClient(**databaseConfig)
        database, collection = configData['query'].values()
        return connection[database][collection]

    def read(self):
        return [_['chatId'] for _ in self.collection.find()]

    def has(self, chatId):
        return chatId in self.read()

    def insert(self, chatId, name, deck, players, game):
        # playerVars = vars(player)
        # if playerVars['hand']:
        #     playerVars['hand'] = [vars(card) for card in player.hand]
        # if playerVars['availableCards']:
        #     playerVars['availableCards'] = [vars(card) for card in player.availableCards]
        data = {'chatId': chatId, 'name': name, 'deck': deck, 'player': players, 'game': game}
        try:
            response = self.collection.insert_one(data)
            print(f'chatId-{chatId} added successfully..')
            # print(response.inserted_id, data)
            # return response
        except pymongo.errors.DuplicateKeyError:
            print('chatId exists, aborting..')
        return

    def delete(self, chatId):
        query = {'chatId': chatId}
        result = list(self.collection.find(query))
        print(result)
        if result:
            if len(result) == 1:
                response = self.collection.delete_one(query)
                print(f'chatId-{chatId} deleted successfully..')
                # return response
            else:
                print(f'Duplicate chatId-{chatId} found, aborting..')
        else:
            print('chatId not found..')
        return

def addUser(name, chatId):
    # Mongo DB Commands
    with open('config.yaml', 'r') as stream:
        try:
            configData = yaml.safe_load(stream)
        except yaml.YAMLError as ERROR:
            print(ERROR)
    
    obj = MongoDb(configData)
    if not obj.has(chatId):
        obj.insert(chatId, name)
        # print(f'{userId} added..')
        return True
    else:
        return False

if __name__ == '__main__':
    
    from user import Player, Bot, Game
    from card import Deck
    A = Player('YOU')
    botNames = ['B', 'C', 'D']
    B, C, D = [Bot(name) for name in botNames]
    players = [A, B, C, D]
    deck = Deck()
    deck._shuffle
    deck.distribute(players)

    game = Game(players, deck)
    firstPlayer = game._randomPlayer
    playerOrder = game.getPlayerOrder(firstPlayer)

    trump = 'spade'
    game.currentBidder = firstPlayer
    game.currentBidder.likelyPartner = [player for player in playerOrder if player != firstPlayer][0].hand[0]
    game.setTrump(trump)
    deck._setGameRules(game)

    # print(vars(A))
    client = MongoDb(loadConfig())
    client.delete('123')
    # print(Deck.saveCards(deck.deck))
    # print()
    # print(Game.savePlayers(players))
    client.insert('123', 'lyx', Deck.saveCards(deck.deck), Game.savePlayers(players), Game.saveGame(game))