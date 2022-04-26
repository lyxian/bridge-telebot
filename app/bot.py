from cryptography.fernet import Fernet
import requests
import logging
import telebot
import time
import os
import re

from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from card import Bid, Card, Deck, Rank, Suit, cardMappings
from user import Game, Player, Bot

# Commands
# /start
# - start bidding
#   > requires replyMarkup

# Comments
# - require db/session management
# ! Check for re-shuffle (TODO)

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

def createEmptyBot():
    TOKEN = getToken()
    bot = telebot.TeleBot(token=TOKEN)

    @bot.message_handler(func=lambda message: True)
    def _start(message):
        return
    return bot

def createBot():
    TOKEN = getToken()

    bot = telebot.TeleBot(token=TOKEN)
    telebot.logger.setLevel(logging.DEBUG)

    @bot.message_handler(commands=["start"])
    def _start(message):
        text = 'Welcome to Bridge-Telebot! ☺ Here are the list of commands to get you started:'
        text += '\n/startgame - Start new game'
        text += '\n/quitgame - Quit existing game'

        if message.chat.id in db.keys():
            if 'pinnedMessageId' in db[message.chat.id].keys():
                bot.unpin_chat_message(message.chat.id, db[message.chat.id]['pinnedMessageId'])
            db[message.chat.id] = {}
        else:
            method = 'getChat'
            params = {
                'chat_id': 315498839
            }
            response = callTelegramAPI(method, params)
            if 'pinned_message' in response.json()['result']:
                pinnedMessageId = response.json()['result']['pinned_message']['message_id']
                method = 'unpinChatMessage'
                params = {
                    'message_id': pinnedMessageId,
                    **params
                }
                response = callTelegramAPI(method, params)
        bot.send_message(message.chat.id, text, reply_markup=ReplyKeyboardRemove())
        return

    @bot.message_handler(commands=["quitgame"])
    def _quitGame(message):
        if message.chat.id in db.keys():
            if 'pinnedMessageId' in db[message.chat.id].keys():
                bot.unpin_chat_message(message.chat.id, db[message.chat.id]['pinnedMessageId'])
            db[message.chat.id] = {}
        else:
            method = 'getChat'
            params = {
                'chat_id': 315498839
            }
            response = callTelegramAPI(method, params)
            if 'pinned_message' in response.json()['result']:
                pinnedMessageId = response.json()['result']['pinned_message']['message_id']
                method = 'unpinChatMessage'
                params = {
                    'message_id': pinnedMessageId,
                    **params
                }
                response = callTelegramAPI(method, params)
        bot.send_message(message.chat.id, 'OK', reply_markup=ReplyKeyboardRemove())
        return

    @bot.message_handler(commands=["startgame"])
    def _startGame(message):
        # Prevent duplicate games
        if message.chat.id in db.keys():
            if db[message.chat.id] != {}:
                return

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
        
        bot.send_message(message.chat.id, game._playerResults)
        bot.pin_chat_message(message.chat.id, message.id+1)


        # bot.send_message(message.chat.id, f'{[i.name for i in playerOrder]}')
        # telebot.logger.debug([i.name for i in playerOrder])

        db[message.chat.id] = {
            'pinnedMessageId': message.id+1,
            'game': game,
            'deck': deck,
            'players': players,
            'playerOrder': playerOrder,
            'continueBidding': True,
            'choosePartnerSuit': False,
            'choosePartnerRank': False,
            'winningBidder': None,
            'player': A
        }
            
        skippedPlayers = []
        bot.send_message(message.chat.id, f'Round bidders: {[i.name for i in playerOrder]}')
        # telebot.logger.debug(f'Round bidders: {[i.name for i in playerOrder]}')

        for player in playerOrder:
            if game.currentBidder and game.currentBidder == player:
                continueBidding = False
                winningBidder = player
                db[message.chat.id]['winningBidder'] = player
                if isinstance(winningBidder, Player):
                    # bot.send_message(message.chat.id, f'Your Hand: {Deck.showBySuitStr(winningBidder.hand)}')
                    if 1:
                        rank, suit = 'ace spade'.split()
                    else:
                        db[message.chat.id]['choosePartnerSuit'] = True
                        bot.send_message(message.chat.id, f'Choose partner suit: ', reply_markup=createMarkupSuits())
                break
            if isinstance(player, Player):
                bot.send_message(message.chat.id, 'Your Cards', reply_markup=createMarkupHand(player.hand))
                # bot.send_message(message.chat.id, f'Your Hand: {Deck.showBySuitStr(player.hand)}', reply_markup=createMarkupBid())
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
        if skippedPlayers:
            for player in skippedPlayers:
                playerOrder.pop(playerOrder.index(player))
            db[message.chat.id]['playerOrder'] = playerOrder

    def checkPartnerSuit(message):
        if message.chat.id not in db.keys():
            return False
        if db[message.chat.id]['choosePartnerSuit']:
            db[message.chat.id]['choosePartnerSuit'] = False
            return True
        else:
            return False

    @bot.message_handler(func=lambda message: checkPartnerSuit(message))
    def _replyPartnerSuit(message):
        # Prevent bot from hanging
        if message.chat.id not in db.keys():
            bot.send_message(message.chat.id, f'Game not found, start new game with /startgame command', reply_markup=ReplyKeyboardRemove())
            return
        winningBidder = db[message.chat.id]['winningBidder']
        if message.text == 'Back':
            bot.delete_message(message.chat.id, message.id-1)
            bot.delete_message(message.chat.id, message.id)
            db[message.chat.id]['choosePartnerSuit'] = True
            bot.send_message(message.chat.id, f'Choose partner suit: ', reply_markup=createMarkupSuits())
        elif message.text == 'Your Cards':
            bot.delete_message(message.chat.id, message.id-1)
            bot.delete_message(message.chat.id, message.id)
            # bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.id-1, reply_markup=createMarkupHand(user.hand))
            bot.send_message(message.chat.id, 'Your Cards', reply_markup=createMarkupHand(winningBidder.hand))
            db[message.chat.id]['choosePartnerSuit'] = True
        else:
            db[message.chat.id]['partnerSuit'] = message.text
            db[message.chat.id]['choosePartnerRank'] = True
            bot.send_message(message.chat.id, f'Choose partner rank: ', reply_markup=createMarkupRanks())

    def checkPartnerRank(message):
        if message.chat.id not in db.keys():
            return False
        if db[message.chat.id]['choosePartnerRank']:
            db[message.chat.id]['choosePartnerRank'] = False
            return True
        else:
            return False
            
    @bot.message_handler(func=lambda message: checkPartnerRank(message))
    def _replyPartnerRank(message):
        # Prevent bot from hanging
        if message.chat.id not in db.keys():
            bot.send_message(message.chat.id, f'Game not found, start new game with /startgame command', reply_markup=ReplyKeyboardRemove())
            return
        winningBidder = db[message.chat.id]['winningBidder']
        if message.text == 'Back':
            bot.delete_message(message.chat.id, message.id-1)
            bot.delete_message(message.chat.id, message.id)
            db[message.chat.id]['choosePartnerSuit'] = True
            bot.send_message(message.chat.id, f'Choose partner suit: ', reply_markup=createMarkupSuits())
        elif message.text == 'Your Cards':
            bot.delete_message(message.chat.id, message.id-1)
            bot.delete_message(message.chat.id, message.id)
            # bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.id-1, reply_markup=createMarkupHand(user.hand))
            bot.send_message(message.chat.id, 'Your Cards', reply_markup=createMarkupHand(winningBidder.hand))
            db[message.chat.id]['choosePartnerSuit'] = True
        else:
            db[message.chat.id]['partnerRank'] = message.text
            # Create card object
            game = db[message.chat.id]['game']
            deck = db[message.chat.id]['deck']
            rank = cardMappings[db[message.chat.id]['partnerRank']]
            suit = cardMappings[db[message.chat.id]['partnerSuit']]
            winningBidder = db[message.chat.id]['winningBidder']
            cardStr = db[message.chat.id]['partnerRank'] + db[message.chat.id]['partnerSuit']

            # Check if card in hands
            if len([card for card in db[message.chat.id]['winningBidder'].hand if card.rank == rank and card.suit == suit]):
                db[message.chat.id]['choosePartnerSuit'] = True
                bot.send_message(message.chat.id, f'{cardStr} found in hand, choose again.\nChoose partner suit: ', reply_markup=createMarkupSuits())
                # telebot.logging(f'Partner card found in own hand, please select partner again')
            else:
                winningBidder.setLikelyPartner([card for card in game.deck.deck if card.rank == rank and card.suit == suit][0])
                # ==Post-Bidding==
                trump = game.currentBid.suit
                game.setTrump(trump)
                deck._setGameRules(game)
                db[message.chat.id]['continueBidding'] = False
                db[message.chat.id]['firstPlayer'] = game.getPlayerOrder(winningBidder)[1]    
                telebot.logging.debug(db[message.chat.id]['remainingPlayers'])
                db[message.chat.id]['remainingPlayers'] = None

                bot.send_message(message.chat.id, f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner}')
                bot.edit_message_text(game._playerResults, message.chat.id, db[message.chat.id]['pinnedMessageId'])
                startPlay(message)

    def checkBid(message):
        if message.chat.id not in db.keys():
            return False
        text = message.text
        if db[message.chat.id]['continueBidding']:
            if text == 'Your Cards' or text == 'Pass' or text =='Back':
                return True
            elif re.search(r'\d(♣|♦|♥|♠|NT)', text):
                return True
            else:
                return False
        else:
            return False

    @bot.message_handler(func=lambda message: checkBid(message))
    def _replyBid(message):
        # Prevent bot from hanging
        if message.chat.id not in db.keys():
            bot.send_message(message.chat.id, f'Game not found, start new game with /startgame command', reply_markup=ReplyKeyboardRemove())
            return
        bot.delete_message(message.chat.id, message.id-1)
        bot.delete_message(message.chat.id, message.id)

        game = db[message.chat.id]['game']
        deck = db[message.chat.id]['deck']
        user = db[message.chat.id]['player']
        playerOrder = db[message.chat.id]['playerOrder']
        remainingPlayers = db[message.chat.id]['remainingPlayers']
        continueBidding = db[message.chat.id]['continueBidding']
        
        # Process player's bid
        text = message.text
        skippedPlayers = []
        if text == 'Your Cards':
            # bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.id-1, reply_markup=createMarkupHand(user.hand))
            bot.send_message(message.chat.id, 'Your Cards', reply_markup=createMarkupHand(user.hand))
            return
        elif text == 'Back':
            bot.send_message(message.chat.id, f'Choose bid: ', reply_markup=createMarkupBid())
            return
        elif text == 'Pass':
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
                db[message.chat.id]['playerOrder'] = playerOrder
            while continueBidding:
                skippedPlayers = []
                # bot.send_message(message.chat.id, f'Round bidders: {[i.name for i in playerOrder]}')
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
                    db[message.chat.id]['playerOrder'] = playerOrder
                time.sleep(0.5)
                
            # ==Post-Bidding==
            trump = game.currentBid.suit
            game.setTrump(trump)
            deck._setGameRules(game)
            db[message.chat.id]['continueBidding'] = continueBidding
            db[message.chat.id]['firstPlayer'] = game.getPlayerOrder(winningBidder)[1]
            telebot.logging.debug(db[message.chat.id]['remainingPlayers'])
            db[message.chat.id]['remainingPlayers'] = None

            if winningBidder.likelyPartner.owner == user:
                bot.send_message(message.chat.id, f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner} (YOU)')
            else:
                bot.send_message(message.chat.id, f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner}')
            bot.edit_message_text(game._playerResults, message.chat.id, db[message.chat.id]['pinnedMessageId'])
            startPlay(message)
            return '', 200
            # telebot.logger.debug(f'{player.name} passed\n')
        else:
            # Validate bid
            bid = Bid(int(text[0]), cardMappings[text[1:]])
            if game.currentBid is None or game.currentBid < bid:
                game.currentBid = bid
                game.currentBidder = user
                bot.send_message(message.chat.id, f'Current bid by {user.name} is: {bid}\n')
            else: # if invalid, ask again
                bot.send_message(message.chat.id, f'You have entered an invalid bid, please try again.\nYour Hand: {Deck.showBySuitStr(user.hand)}', reply_markup=createMarkupBid())
                return

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
                db[message.chat.id]['playerOrder'] = playerOrder

        for player in playerOrder:
            if game.currentBidder and game.currentBidder == player:
                continueBidding = False
                winningBidder = player
                if isinstance(winningBidder, Player):
                    db[message.chat.id]['winningBidder'] = player
                    # bot.send_message(message.chat.id, f'Your Hand: {Deck.showBySuitStr(winningBidder.hand)}')
                    if 0:
                        bot.send_message(message.chat.id, f'Choose Partner: ', reply_markup=ReplyKeyboardRemove())
                        db[message.chat.id]['playerTurn'] = True
                    else:
                        db[message.chat.id]['continueBidding'] = continueBidding
                        db[message.chat.id]['choosePartnerSuit'] = True
                        bot.send_message(message.chat.id, f'Choose partner suit: ', reply_markup=createMarkupSuits())
                    break
                # ==Post-Bidding==
                trump = game.currentBid.suit
                game.setTrump(trump)
                deck._setGameRules(game)
                db[message.chat.id]['continueBidding'] = continueBidding
                db[message.chat.id]['firstPlayer'] = game.getPlayerOrder(winningBidder)[1]    
                telebot.logging.debug(db[message.chat.id]['remainingPlayers'])
                db[message.chat.id]['remainingPlayers'] = None

                if winningBidder.likelyPartner.owner == user:
                    bot.send_message(message.chat.id, f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner} (YOU)')
                else:
                    bot.send_message(message.chat.id, f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner}')
                bot.edit_message_text(game._playerResults, message.chat.id, db[message.chat.id]['pinnedMessageId'])
                startPlay(message)
                return '', 200
            if isinstance(player, Player):
                bot.send_message(message.chat.id, 'Your Cards', reply_markup=createMarkupHand(player.hand))
                # bot.send_message(message.chat.id, f'Your Hand: {Deck.showBySuitStr(player.hand)}', reply_markup=createMarkupBid())
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
                # playerOrder.pop(playerOrder.index(player))
                db[message.chat.id]['playerOrder'] = playerOrder
            else:
                game.currentBid = bid
                game.currentBidder = player
                bot.send_message(message.chat.id, f'Current bid by {player.name} is: {bid}\n')
                # telebot.logger.debug(f'Current bid by {player.name} is: {bid}\n')
        if skippedPlayers:
            for player in skippedPlayers:
                playerOrder.pop(playerOrder.index(player))
            db[message.chat.id]['playerOrder'] = playerOrder
        return '', 200

    def checkPartner(message):
        if message.chat.id not in db.keys():
            return False
        text = message.text
        if 'playerTurn' in db[message.chat.id].keys():
            if db[message.chat.id]['playerTurn']:
                db[message.chat.id]['playerTurn'] = False
                return True
            else:
                return False
        else:
            return False

    @bot.message_handler(func=lambda message: checkPartner(message))
    def _replyPlayerPartner(message):
        # Prevent bot from hanging
        if message.chat.id not in db.keys():
            bot.send_message(message.chat.id, f'Game not found, start new game with /startgame command', reply_markup=ReplyKeyboardRemove())
            return
        game = db[message.chat.id]['game']
        deck = db[message.chat.id]['deck']
        winningBidder = db[message.chat.id]['player']

        rank, suit = message.text.lower().split()
        winningBidder.setLikelyPartner([card for card in deck.deck if card.rank == rank and card.suit == suit][0])
        # ==Post-Bidding==
        trump = game.currentBid.suit
        game.setTrump(trump)
        deck._setGameRules(game)
        db[message.chat.id]['continueBidding'] = False
        db[message.chat.id]['firstPlayer'] = game.getPlayerOrder(winningBidder)[1]    
        telebot.logging.debug(db[message.chat.id]['remainingPlayers'])
        db[message.chat.id]['remainingPlayers'] = None

        bot.send_message(message.chat.id, f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner}')
        bot.edit_message_text(game._playerResults, message.chat.id, db[message.chat.id]['pinnedMessageId'])
        startPlay(message)

    def startPlay(message):
        # ==Playing==
        game = db[message.chat.id]['game']
        deck = db[message.chat.id]['deck']
        user = db[message.chat.id]['player']
        bidSuit = game.currentBid.suit
        if bidSuit == 'notrump':
            firstPlayer = game.currentBidder
        else:
            firstPlayer = game.getPlayerOrder(game.currentBidder)[1]
        playerOrder = game.getPlayerOrder(firstPlayer)

        count = 0
        db[message.chat.id]['count'] = count
            
        playerOrder = game.getPlayerOrder(firstPlayer)
        game.setRoundSuit(count)
        game.resetRoundCards()

        for player in playerOrder:
            if isinstance(player, Player):
                playerMessage = ''
                if game.roundSuit:
                    playerMessage += f'Round Suit: {game.roundSuit}\n'
                # print('Played Cards: ', end='')
                if game.playedCards:
                    playerMessage += ', '.join([f'{card.owner.name}: {card}' for card in game.playedCards])
                else:
                    playerMessage += f'{player.name} plays first'
                roundMessage = bot.send_message(message.chat.id, f'{playerMessage}')
                print(f'\nSetting {roundMessage.id} as Round Message ID\n')
                game.setRoundMessageId(roundMessage.id)

                if player.canFollow(game):
                    player.availableCards = [_ for _ in player.hand if _.suit == game.roundSuit]
                else:
                    if game.roundCount <= 1 or (not game.brokeTrump and not game.playedCards):
                        # print('No trump allowed')
                        player.availableCards = [_ for _ in player.hand if _.suit != game.trump]
                    else:
                        player.availableCards = player.hand
                bot.send_message(message.chat.id, f'Your Hand: ', reply_markup=createMarkupPlay(player.availableCards, False))
                idx = playerOrder.index(player)
                if idx != 3:
                    db[message.chat.id]['remainingPlayers'] = playerOrder[idx+1:]
                else:
                    db[message.chat.id]['remainingPlayers'] = None
                break
            else:
                playedCard = player.play(game)
                game.addRoundCards(playedCard)
                if playedCard == game.currentBidder.likelyPartner:
                    bot.send_message(message.chat.id, '*******************************')
                    game.currentBidder.partner = playedCard.owner
                    game.otherTeam[0].partner = game.otherTeam[1]
                    game.otherTeam[1].partner = game.otherTeam[0]
                if game.roundSuit is None:
                    game.setRoundSuit(count+1, playedCard.suit)
                    deck._setRoundRules(game)

    def checkPlay(message):
        if message.chat.id not in db.keys():
            return False
        text = message.text
        if not db[message.chat.id]['continueBidding']:
            return True
        else:
            return False

    @bot.message_handler(func=lambda message: checkPlay(message))
    def _replyPlay(message):
        # Prevent bot from hanging
        if message.chat.id not in db.keys():
            bot.send_message(message.chat.id, f'Game not found, start new game with /startgame command', reply_markup=ReplyKeyboardRemove())
            return
        bot.delete_message(message.chat.id, message.id-1)
        bot.delete_message(message.chat.id, message.id)
        
        # ==Playing==
        game = db[message.chat.id]['game']
        deck = db[message.chat.id]['deck']
        user = db[message.chat.id]['player']
        # firstPlayer = game.getPlayerOrder(game.currentBidder)[1]
        # playerOrder = game.getPlayerOrder(firstPlayer)
        count = db[message.chat.id]['count']

        # Look at hand
        if message.text == 'Your Cards':
            bot.send_message(message.chat.id, f'Your Hand: ', reply_markup=createMarkupPlay(user.hand, True))
            return
        elif message.text == 'Back':
            bot.send_message(message.chat.id, f'Your Hand: ', reply_markup=createMarkupPlay(user.availableCards, False))
            return

        # Check if card is valid
        cardSuit = cardMappings[message.text[-1]]
        if game.roundSuit:
            if user.canFollow(game) and cardSuit != game.roundSuit:
                bot.send_message(message.chat.id, f'Invalid move!\nYour Hand: ', reply_markup=createMarkupPlay(user.availableCards, False))
                return
            else:
                if game.roundCount <= 1 and cardSuit == game.trump:
                    bot.send_message(message.chat.id, f'Invalid move!\nYour Hand: ', reply_markup=createMarkupPlay(user.availableCards, False))
                    return
        else:
            if not game.brokeTrump and cardSuit == game.trump and game.roundCount <= 1:
                bot.send_message(message.chat.id, f'Invalid move!\nYour Hand: ', reply_markup=createMarkupPlay(user.availableCards, False))
                return

        playedCard = user.hand.pop(user._handIndex[message.text])
        game.addRoundCards(playedCard)
        if playedCard == game.currentBidder.likelyPartner:
            bot.send_message(message.chat.id, '*******************************')
            game.currentBidder.partner = playedCard.owner
            game.otherTeam[0].partner = game.otherTeam[1]
            game.otherTeam[1].partner = game.otherTeam[0]
        if game.roundSuit is None:
            game.setRoundSuit(count, playedCard.suit)
            deck._setRoundRules(game)

        if len(game.playedCards) == 4:
            winningCard = sorted(game.playedCards, reverse=True)[0]
            text = ' | '.join([f'{card.owner.name}: {card}' for card in game.playedCards])
            bot.edit_message_text(f'Round Suit: {game.roundSuit}\n{text}\n<b>{winningCard.owner.name} wins with {winningCard}</b>', message.chat.id, game.roundMessageId, parse_mode='html')
            # bot.send_message(message.chat.id, f'Round Suit: {game.roundSuit}\n{text}\n**{winningCard.owner.name} wins with {winningCard}**')
            firstPlayer = winningCard.owner
            firstPlayer.tricks += 1
            playerOrder = game.getPlayerOrder(firstPlayer)
            bot.edit_message_text(game._playerResults, message.chat.id, db[message.chat.id]['pinnedMessageId'])
        else: #if db[message.chat.id]['remainingPlayers']:
            for player in db[message.chat.id]['remainingPlayers']:
                playedCard = player.play(game)
                game.addRoundCards(playedCard)
                if playedCard == game.currentBidder.likelyPartner:
                    bot.send_message(message.chat.id, '*******************************')
                    game.currentBidder.partner = playedCard.owner
                    game.otherTeam[0].partner = game.otherTeam[1]
                    game.otherTeam[1].partner = game.otherTeam[0]
                if game.roundSuit is None:
                    game.setRoundSuit(count, playedCard.suit)
                    deck._setRoundRules(game)
            winningCard = sorted(game.playedCards, reverse=True)[0]
            text = ' | '.join([f'{card.owner.name}: {card}' for card in game.playedCards])
            bot.edit_message_text(f'Round Suit: {game.roundSuit}\n{text}\n<b>{winningCard.owner.name} wins with {winningCard}</b>', message.chat.id, game.roundMessageId, parse_mode='html')
            # bot.send_message(message.chat.id, f'{text}\n{winningCard.owner.name} wins with {winningCard}')
            firstPlayer = winningCard.owner
            firstPlayer.tricks += 1
            playerOrder = game.getPlayerOrder(firstPlayer)
            bot.edit_message_text(game._playerResults, message.chat.id, db[message.chat.id]['pinnedMessageId'])

        db[message.chat.id]['count'] += 1
        count = db[message.chat.id]['count']
        if count >= 13:
            bot.send_message(message.chat.id, f'==={game.currentBid} Game Ended===\n{game._results}\n{game._teamResults}', reply_markup=ReplyKeyboardRemove())
            bot.unpin_chat_message(message.chat.id, db[message.chat.id]['pinnedMessageId'])
            db[message.chat.id] = {}
        else:
            playerOrder = game.getPlayerOrder(firstPlayer)
            game.setRoundSuit(count)
            game.resetRoundCards()

            for player in playerOrder:
                if isinstance(player, Player):
                    playerMessage = ''
                    if game.roundSuit:
                        playerMessage += f'Round Suit: {game.roundSuit}\n'
                    # print('Played Cards: ', end='')
                    if game.playedCards:
                        playerMessage += ', '.join([f'{card.owner.name}: {card}' for card in game.playedCards])
                    else:
                        playerMessage += f'{player.name} plays first'
                    roundMessage = bot.send_message(message.chat.id, f'{playerMessage}')
                    print(f'\nSetting {roundMessage.id} as Round Message ID\n')
                    game.setRoundMessageId(roundMessage.id)
                    if player.canFollow(game):
                        player.availableCards = [_ for _ in player.hand if _.suit == game.roundSuit]
                    else:
                        if game.roundCount <= 0 or (not game.brokeTrump and not game.playedCards):
                            # print('No trump allowed')
                            player.availableCards = [_ for _ in player.hand if _.suit != game.trump]
                        else:
                            player.availableCards = player.hand
                    bot.send_message(message.chat.id, f'Your Hand: ', reply_markup=createMarkupPlay(player.availableCards, False))
                    idx = playerOrder.index(player)
                    if idx != 3:
                        db[message.chat.id]['remainingPlayers'] = playerOrder[idx+1:]
                    else:
                        db[message.chat.id]['remainingPlayers'] = None
                    break
                else:
                    playedCard = player.play(game)
                    game.addRoundCards(playedCard)
                    if playedCard == game.currentBidder.likelyPartner:
                        bot.send_message(message.chat.id, '*******************************')
                        game.currentBidder.partner = playedCard.owner
                        game.otherTeam[0].partner = game.otherTeam[1]
                        game.otherTeam[1].partner = game.otherTeam[0]
                    if game.roundSuit is None:
                        game.setRoundSuit(count+1, playedCard.suit)
                        deck._setRoundRules(game)

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

    return bot
    
if __name__ == "__main__":
    bot = createBot()