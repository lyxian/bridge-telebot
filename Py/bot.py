from cryptography.fernet import Fernet
import requests
import logging
import telebot
import time
import os
import re

from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from card import Bid, Deck, cardMappings
from user import Game, Player, Bot

# Commands
# /start
# - start bidding
#   > requires replyMarkup

# Comments
# - require db/session management

db = {}

def getToken():
    key = bytes(os.getenv("KEY"), "utf-8")
    encrypted = bytes(os.getenv("SECRET_TELEGRAM"), "utf-8")
    return Fernet(key).decrypt(encrypted).decode()

def callTelegramAPI(method, params):
    url = 'https://api.telegram.org/bot{}/{}'.format(getToken(), method)
    response = requests.post(url=url, params=params)
    print(response.json())
    return response

def createBot():
    TOKEN = getToken()

    bot = telebot.TeleBot(token=TOKEN)
    telebot.logger.setLevel(logging.DEBUG)

    @bot.message_handler(commands=["start"])
    def _start(message):
        # ===Game Start===
        deck = Deck()
        deck._shuffle
        # deck._show
        botNames = ['B', 'C', 'D']
        A = Player('YOU')
        B, C, D = [Bot(name) for name in botNames]
        players = [A, B, C, D]
        deck.distribute(players)

        # ==Bidding==
        game = Game(players, deck)
        firstPlayer = game._randomPlayer
        playerOrder = game.getPlayerOrder(firstPlayer)
        
        bot.send_message(message.chat.id, f'{[i.name for i in playerOrder]}')
        # telebot.logger.debug([i.name for i in playerOrder])

        db[message.chat.id] = {
            'game': game,
            'deck': deck,
            'players': players,
            'playerOrder': playerOrder,
            'continueBidding': True,
            'player': A
        }
            
        skippedPlayers = []
        bot.send_message(message.chat.id, f'Round bidders: {[i.name for i in playerOrder]}')
        # telebot.logger.debug(f'Round bidders: {[i.name for i in playerOrder]}')

        for player in playerOrder:
            if game.currentBidder and game.currentBidder == player:
                continueBidding = False
                winningBidder = player
                if isinstance(winningBidder, Player):
                    bot.send_message(message.chat.id, f'Your Hand: {Deck.showBySuitStr(winningBidder.hand)}')
                    # print(f'Your Hand: {Deck.showBySuitStr(winningBidder.hand)}')
                    rank, suit = 'ace spade'.split()
                    # rank, suit = input('Enter partner (eg. "ace spade"): ').split()
                    winningBidder.setLikelyPartner([card for card in game.deck.deck if card.rank == rank and card.suit == suit][0])
                break
            if isinstance(player, Player):
                bot.send_message(message.chat.id, f'Your Hand: {Deck.showBySuitStr(player.hand)}', reply_markup=createMarkup())
                idx = playerOrder.index(player)
                if idx != 3:
                    db[message.chat.id]['remainingPlayers'] = playerOrder[idx+1:]
                else:
                    db[message.chat.id]['remainingPlayers'] = None
                if skippedPlayers:
                    for player in skippedPlayers:
                        playerOrder.pop(playerOrder.index(player))
                    db[message.chat.id]['playerOrder'] = playerOrder
                break
                # telebot.logger.debug(Deck.showBySuitStr(player.hand))

                # START PLAYER BIDDING
                # minBid = input('Enter min. bid: ')
                # if minBid == 'pass':
                #     bid = minBid
                # bestSuit = input('Enter suit: ')
                # if bestSuit == 'pass':
                #     bid = bestSuit
                # bidObj = Bid(int(minBid), bestSuit)
                # if game.currentBid is None or game.currentBid < bidObj:
                #     bid = bidObj
                # else:
                #     bid = 'pass'
            else:
                bid = player.bid(game)
            if bid == 'Pass':
                skippedPlayers.append(player)
                bot.send_message(message.chat.id, f'{player.name} passed\n')
                # telebot.logger.debug(f'{player.name} passed\n')
            else:
                game.currentBid = bid
                game.currentBidder = player
                bot.send_message(message.chat.id, f'Current bid by {player.name} is: {bid}\n')
                # telebot.logger.debug(f'Current bid by {player.name} is: {bid}\n')
                    
        # ==Post-Bidding==
        # if game.currentBid is None:
        #     trump = 'spade'
        #     winningBidder = firstPlayer
        #     winningBidder.likelyPartner = firstPlayer
        # else:
        #     trump = game.currentBid.suit
        # game.setTrump(trump)
        # deck._setGameRules(game)

        # bot.send_message(message.chat.id, "Enter bid:", reply_markup=createMarkup())
        # pass

    def checkBid(message):
        text = message.text
        if db[message.chat.id]['continueBidding']:
            if text == 'More' or text == 'Pass':
                return True
            elif re.search(r'\d(♣|♦|♥|♠|NT)', text):
                return True
            else:
                return False
        else:
            return False

    @bot.message_handler(func=lambda message: checkBid(message))
    def _replyBid(message):
        game = db[message.chat.id]['game']
        deck = db[message.chat.id]['deck']
        user = db[message.chat.id]['player']
        playerOrder = db[message.chat.id]['playerOrder']
        remainingPlayers = db[message.chat.id]['remainingPlayers']
        continueBidding = db[message.chat.id]['continueBidding']

        # Process player's bid
        text = message.text
        skippedPlayers = []
        if text == 'Pass':
            skippedPlayers.append(user)
            bot.send_message(message.chat.id, f'{user.name} passed\n')

            if remainingPlayers:
                for player in remainingPlayers:
                    if game.currentBidder and game.currentBidder == player:
                        continueBidding = False
                        winningBidder = player
                        game.askPlayer(player)
                        break
                    bid = player.bid(game)
                    if bid == 'Pass':
                        skippedPlayers.append(player)
                        bot.send_message(message.chat.id, f'{player.name} passed\n')
                        # telebot.logger.debug(f'{player.name} passed\n')
                    else:
                        game.currentBid = bid
                        game.currentBidder = player
                        bot.send_message(message.chat.id, f'Current bid by {player.name} is: {bid}\n')
            if skippedPlayers:
                for player in skippedPlayers:
                    playerOrder.pop(playerOrder.index(player))
                pass
            while continueBidding:
                skippedPlayers = []
                bot.send_message(message.chat.id, f'Round bidders: {[i.name for i in playerOrder]}')
                for player in playerOrder:
                    if game.currentBidder and game.currentBidder == player:
                        continueBidding = False
                        winningBidder = player
                        game.askPlayer(player)
                        break
                    bid = player.bid(game)
                    if bid == 'Pass':
                        skippedPlayers.append(player)
                        bot.send_message(message.chat.id, f'{player.name} passed\n')
                    else:
                        game.currentBid = bid
                        game.currentBidder = player
                        bot.send_message(message.chat.id, f'Current bid by {player.name} is: {bid}\n')
                    
                if skippedPlayers:
                    for player in skippedPlayers:
                        playerOrder.pop(playerOrder.index(player))
                time.sleep(1)
                
            bot.send_message(message.chat.id, 'DONE BIDDING')
            # ==Post-Bidding==
            trump = game.currentBid.suit
            game.setTrump(trump)
            deck._setGameRules(game)

            if winningBidder.likelyPartner.owner == user:
                bot.send_message(message.chat.id, f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner} (YOU)')
            else:
                bot.send_message(message.chat.id, f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner}')
            return '', 200
            # telebot.logger.debug(f'{player.name} passed\n')
        else:
            bid = Bid(int(text[0]), cardMappings[text[1:]])
            game.currentBid = bid
            game.currentBidder = user
            bot.send_message(message.chat.id, f'Current bid by {user.name} is: {bid}\n')

        # Let remaining players bid for current round
        skippedPlayers = []
        if remainingPlayers:
            for player in remainingPlayers:
                bid = player.bid(game)
                if bid == 'Pass':
                    skippedPlayers.append(player)
                    bot.send_message(message.chat.id, f'{player.name} passed\n')
                    # telebot.logger.debug(f'{player.name} passed\n')
                else:
                    game.currentBid = bid
                    game.currentBidder = player
                    bot.send_message(message.chat.id, f'Current bid by {player.name} is: {bid}\n')
            if skippedPlayers:
                for player in skippedPlayers:
                    playerOrder.pop(playerOrder.index(player))

        for player in playerOrder:
            if game.currentBidder and game.currentBidder == player:
                continueBidding = False
                winningBidder = player
                if isinstance(winningBidder, Player):
                    bot.send_message(message.chat.id, f'Your Hand: {Deck.showBySuitStr(winningBidder.hand)}')
                    # print(f'Your Hand: {Deck.showBySuitStr(winningBidder.hand)}')
                    rank, suit = 'ace spade'.split()
                    # rank, suit = input('Enter partner (eg. "ace spade"): ').split()
                    winningBidder.setLikelyPartner([card for card in game.deck.deck if card.rank == rank and card.suit == suit][0])
                bot.send_message(message.chat.id, 'DONE BIDDING')
                # ==Post-Bidding==
                trump = game.currentBid.suit
                game.setTrump(trump)
                deck._setGameRules(game)

                if winningBidder.likelyPartner.owner == user:
                    bot.send_message(message.chat.id, f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner} (YOU)')
                else:
                    bot.send_message(message.chat.id, f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner}')
                return '', 200
            if isinstance(player, Player):
                bot.send_message(message.chat.id, f'Your Hand: {Deck.showBySuitStr(player.hand)}', reply_markup=createMarkup())
                idx = playerOrder.index(player)
                if idx != 3:
                    db[message.chat.id]['remainingPlayers'] = playerOrder[idx+1:]
                else:
                    db[message.chat.id]['remainingPlayers'] = None
                if skippedPlayers:
                    for player in skippedPlayers:
                        playerOrder.pop(playerOrder.index(player))
                    db[message.chat.id]['playerOrder'] = playerOrder
                break
            else:
                bid = player.bid(game)
            if bid == 'Pass':
                skippedPlayers.append(player)
                bot.send_message(message.chat.id, f'{player.name} passed\n')
                # telebot.logger.debug(f'{player.name} passed\n')
            else:
                game.currentBid = bid
                game.currentBidder = player
                bot.send_message(message.chat.id, f'Current bid by {player.name} is: {bid}\n')
                # telebot.logger.debug(f'Current bid by {player.name} is: {bid}\n')

        # db[message.chat.id]['playerOrder'] = playerOrder
        # telebot.logger.debug(message)
        return '', 200

    def checkPlay(messsage):
        pass

    @bot.message_handler(func=lambda message: checkPlay(message))
    def _replyPlay(message):
        telebot.logger.debug(message)
        pass

    def createMarkup():
        # Using the ReplyKeyboardMarkup class
        # It's constructor can take the following optional arguments:
        # - resize_keyboard: True/False (default False)
        # - one_time_keyboard: True/False (default False)
        # - selective: True/False (default False)
        # - row_width: integer (default 3)
        # row_width is used in combination with the add() function.
        # It defines how many buttons are fit on each row before continuing on the next row.

        markup = ReplyKeyboardMarkup(row_width=5)
        # Add Numbers
        for i in range(3):
            markup.add(
                *[KeyboardButton(f'{i+1}{suit}') for suit in ['♣', '♦', '♥', '♠', 'NT']]
            )
        markup.add(
            KeyboardButton('Pass'), KeyboardButton('More')
        )
        return markup

    return bot
    
if __name__ == "__main__":
    bot = createBot()