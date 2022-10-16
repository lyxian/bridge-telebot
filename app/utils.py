from cryptography.fernet import Fernet
import requests
import pymongo
import yaml
import os

def retrieveKey():
    required = ['APP_NAME', 'APP_PASS', 'STORE_PASS', 'STORE_URL']
    if all(param in os.environ for param in required):
        payload = {
            'url': '{}/{}'.format(os.getenv('STORE_URL'), 'getPass'),
            'payload': {
                'password': int(os.getenv('STORE_PASS')),
                'app': os.getenv('APP_NAME'),
                'key': int(os.getenv('APP_PASS'))
            }
        }
        response = requests.post(payload['url'], json=payload['payload']).json()
        if response.get('status') == 'OK':
            key = response.get('KEY')
            os.environ['KEY'] = key
            return key
        else:
            raise Exception('Bad response from KEY_STORE, please try again ..')
    else:
        raise Exception('No key store found, please check config ..')

def postError(error):
    required = ['APP_NAME', 'APP_PASS', 'STORE_PASS', 'STORE_URL']
    if all(param in os.environ for param in required):
        payload = {
            'url': '{}/{}'.format(os.getenv('STORE_URL'), 'postError'),
            'payload': {
                'password': int(os.getenv('STORE_PASS')),
                'app': os.getenv('APP_NAME'),
                'key': int(os.getenv('APP_PASS')),
                'error': error,
            }
        }
        response = requests.post(payload['url'], json=payload['payload']).json()
        if response.get('status') == 'OK':
            return response
        else:
            raise Exception('Bad response from KEY_STORE, please try again ..')
    else:
        raise Exception('No key store found, please check config ..')

def getToken():
    key = bytes(retrieveKey(), 'utf-8')
    encrypted = bytes(os.getenv('SECRET_TELEGRAM'), 'utf-8')
    return Fernet(key).decrypt(encrypted).decode()

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

    def insert(self, chatId, name):
        data = {'chatId': chatId, 'name': name}
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

# Message Filter
from enum import Enum
class Filter(Enum):
    replyPartnerSuit = 1
    replyPartnerRank = 2
    replyBid = 3
    replyPlayerPartner = 4
    replyPlay = 5

# Reply Markups
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from card import Deck, Rank, Suit, cardMappings

def createMarkupBid():
    markup = ReplyKeyboardMarkup(row_width=5)
    # Add Numbers
    for i in range(4):
        markup.add(
            *[KeyboardButton(f'{i+1}{suit}') for suit in ['♣', '♦', '♥', '♠', 'NT']]
        )
    markup.add(
        KeyboardButton('Pass'), KeyboardButton('Your Cards')
    )
    return markup

def createMarkupPlay(cards, showAll):
    n = len(cards)
    if n > 3:
        if n == 4:
            grid = [2,2]
        elif n == 5:
            grid = [3,2]
        elif n == 6:
            grid = [3,3]
        elif n == 7:
            grid = [4,3]
        elif n == 8:
            grid = [4,4]
        elif n == 9:
            grid = [3,3,3]
        elif n == 10:
            grid = [4,3,3]
        elif n == 11:
            grid = [4,4,3]
        elif n == 12:
            grid = [4,4,4]
        else:
            grid = [4,3,3,3]
    else:
        grid = [n]

    markup = ReplyKeyboardMarkup(row_width=grid[0])
    count = 0
    for row in grid:
        markup.add(
            *[KeyboardButton(str(cards[i+sum(grid[:count])]).strip()) for i in range(row)]
        )
        count += 1
    if showAll:
        markup.add(KeyboardButton('Back'))
    else:
        markup.add(KeyboardButton('Your Cards'))
    return markup

def createMarkupHand(cards):
    markup = ReplyKeyboardMarkup(row_width=4)
    hand = Deck.showBySuit(cards)
    suits = Suit._member_names_[:4]
    # Add header
    markup.add(
        *[KeyboardButton(f'{cardMappings[suit]}') for suit in suits]
    )
    n = max([len(i) for i in hand.values()])
    for i in range(n):
        markup.add(
            *[KeyboardButton(f'{hand[suit][i]}') if len(hand[suit]) > i else KeyboardButton('-') for suit in suits]
        )
    markup.add(
        KeyboardButton('Back')
    )
    return markup

def createMarkupSuits():
    markup = ReplyKeyboardMarkup(row_width=2)
    suits = Suit._member_names_[3::-1]
    grid = [2,2]
    count = 0
    for row in grid:
        markup.add(
            *[KeyboardButton(f'{cardMappings[suits[count+i]]}') for i in range(row)]
        )
        count += row
    markup.add(
        KeyboardButton('Back'), KeyboardButton('Your Cards')
    )
    return markup

def createMarkupRanks():
    markup = ReplyKeyboardMarkup(row_width=4)
    ranks = Rank._member_names_[::-1]
    grid = [4,3,3,3]
    count = 0
    for row in grid:
        markup.add(
            *[KeyboardButton(f'{cardMappings[ranks[count+i]]}') for i in range(row)]
        )
        count += row
    markup.add(
        KeyboardButton('Back'), KeyboardButton('Your Cards')
    )
    return markup

if __name__ == '__main__':
    pass