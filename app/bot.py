import requests
import logging
import telebot
import time
import re

from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from card import Bid, Card, Deck, Rank, Suit, cardMappings
from user import Game, Player, Bot
from utils import getToken, Filter, createMarkupBid, createMarkupPlay, createMarkupHand, createMarkupSuits, createMarkupRanks

# Commands
# /start
# - start bidding
#   > requires replyMarkup

# Comments
# - require db/session management
# ! Check for re-shuffle (TODO)

db = {}

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
        game = Game(players, deck, message.chat.id)
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
            bid = player.bid(game)
            if isinstance(player, Player):
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

    def messageFilter(message, mode):
        # Check if user has existing game
        if message.chat.id not in db.keys():
            bot.send_message(message.chat.id, f'Game not found, start new game with /startgame command', reply_markup=ReplyKeyboardRemove())
            return False
        
        text = message.text
        # Check message and trigger respective function
        if mode == Filter.replyPartnerSuit:
            if db[message.chat.id]['choosePartnerSuit']:
                db[message.chat.id]['choosePartnerSuit'] = False
                return True
            else:
                return False
        elif mode == Filter.replyPartnerRank:
            if db[message.chat.id]['choosePartnerRank']:
                db[message.chat.id]['choosePartnerRank'] = False
                return True
            else:
                return False
        elif mode == Filter.replyBid:
            if db[message.chat.id]['continueBidding']:
                if text == 'Your Cards' or text == 'Pass' or text =='Back':
                    return True
                elif re.search(r'\d(♣|♦|♥|♠|NT)', text):
                    return True
                else:
                    return False
            else:
                return False
        elif mode == Filter.replyPlayerPartner:
            if 'playerTurn' in db[message.chat.id].keys():
                if db[message.chat.id]['playerTurn']:
                    db[message.chat.id]['playerTurn'] = False
                    return True
                else:
                    return False
            else:
                return False
        elif mode == Filter.replyPlay:
            if not db[message.chat.id]['continueBidding']:
                return True
            else:
                return False

        # bot.send_message('Not handled') 
        return False

    @bot.message_handler(func=lambda message: messageFilter(message, Filter.replyBid))
    def _replyBid(message):
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
                bot.send_message(message.chat.id, f'Invalid bid, choose again: ', reply_markup=createMarkupBid())
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
                game.setTrump(game.currentBid.suit)
                deck._setGameRules(game)
                db[message.chat.id]['continueBidding'] = continueBidding
                # db[message.chat.id]['remainingPlayers'] = None

                if winningBidder.likelyPartner.owner == user:
                    bot.send_message(message.chat.id, f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner} (YOU)')
                else:
                    bot.send_message(message.chat.id, f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner}')
                bot.edit_message_text(game._playerResults, message.chat.id, db[message.chat.id]['pinnedMessageId'])
                startPlay(message)
                return '', 200
            bid = player.bid(game)
            if isinstance(player, Player):
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
                if bid == 'Pass':
                    skippedPlayers.append(player)
                    bot.send_message(message.chat.id, f'{player.name} passed\n')
                    db[message.chat.id]['playerOrder'] = playerOrder
                else:
                    game.currentBid = bid
                    game.currentBidder = player
                    bot.send_message(message.chat.id, f'Current bid by {player.name} is: {bid}\n')
        if skippedPlayers:
            for player in skippedPlayers:
                playerOrder.pop(playerOrder.index(player))
            db[message.chat.id]['playerOrder'] = playerOrder
        return '', 200
            
    @bot.message_handler(func=lambda message: messageFilter(message, Filter.replyPartnerSuit))
    def _replyPartnerSuit(message):
        winningBidder = db[message.chat.id]['winningBidder']
        if message.text in ['Back', 'Your Cards']:
            bot.delete_message(message.chat.id, message.id-1)
            bot.delete_message(message.chat.id, message.id)
            db[message.chat.id]['choosePartnerSuit'] = True
            if message.text == 'Back':
                bot.send_message(message.chat.id, f'Choose partner suit: ', reply_markup=createMarkupSuits())
            elif message.text == 'Your Cards':
                bot.send_message(message.chat.id, 'Your Cards', reply_markup=createMarkupHand(winningBidder.hand))
        else:
            db[message.chat.id]['partnerSuit'] = message.text
            db[message.chat.id]['choosePartnerRank'] = True
            bot.send_message(message.chat.id, f'Choose partner rank: ', reply_markup=createMarkupRanks())
            
    @bot.message_handler(func=lambda message: messageFilter(message, Filter.replyPartnerRank))
    def _replyPartnerRank(message):
        winningBidder = db[message.chat.id]['winningBidder']
        if message.text in ['Back', 'Your Cards']:
            bot.delete_message(message.chat.id, message.id-1)
            bot.delete_message(message.chat.id, message.id)
            db[message.chat.id]['choosePartnerSuit'] = True
            if message.text == 'Back':
                bot.send_message(message.chat.id, f'Choose partner suit: ', reply_markup=createMarkupSuits())
            elif message.text == 'Your Cards':
                bot.send_message(message.chat.id, 'Your Cards', reply_markup=createMarkupHand(winningBidder.hand))
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
            if Deck.findCard(db[message.chat.id]['winningBidder'].hand, suit, rank):
                db[message.chat.id]['choosePartnerSuit'] = True
                bot.send_message(message.chat.id, f'{cardStr} found in hand, choose again.', reply_markup=createMarkupSuits())
            else:
                winningBidder.setLikelyPartner(Deck.findCard(game.deck.deck, suit, rank))
                # ==Post-Bidding==
                game.setTrump(game.currentBid.suit)
                deck._setGameRules(game)
                db[message.chat.id]['continueBidding'] = False

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

    @bot.message_handler(func=lambda message: messageFilter(message, Filter.replyPlay))
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
        if game._hasEnded or count >= 13:
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

    return bot
    
if __name__ == "__main__":
    bot = createBot()