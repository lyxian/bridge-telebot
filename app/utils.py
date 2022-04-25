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

if __name__ == '__main__':
    pass