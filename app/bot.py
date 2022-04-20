from cryptography.fernet import Fernet
import requests
import logging
import telebot
import time
import os
import re

from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from card import Bid, Deck, cardMappings
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
                bot.send_message(message.chat.id, f'Your Hand: {Deck.showBySuitStr(player.hand)}', reply_markup=createMarkupBid())
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
            db[message.chat.id]['continueBidding'] = continueBidding
            db[message.chat.id]['firstPlayer'] = game.getPlayerOrder(winningBidder)[1]
            telebot.logging.debug(db[message.chat.id]['remainingPlayers'])
            db[message.chat.id]['remainingPlayers'] = None

            if winningBidder.likelyPartner.owner == user:
                bot.send_message(message.chat.id, f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner} (YOU)')
            else:
                bot.send_message(message.chat.id, f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner}')
            startPlay(message)
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
                    bot.send_message(message.chat.id, f'Choose Partner: ', reply_markup=ReplyKeyboardRemove())
                    db[message.chat.id]['playerTurn'] = True
                    break
                bot.send_message(message.chat.id, 'DONE BIDDING')
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
                startPlay(message)
                return '', 200
            if isinstance(player, Player):
                bot.send_message(message.chat.id, f'Your Hand: {Deck.showBySuitStr(player.hand)}', reply_markup=createMarkupBid())
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

    def checkPartner(message):
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
        game = db[message.chat.id]['game']
        deck = db[message.chat.id]['deck']
        winningBidder = db[message.chat.id]['player']

        rank, suit = message.text.lower().split()
        winningBidder.setLikelyPartner([card for card in deck.deck if card.rank == rank and card.suit == suit][0])
        bot.send_message(message.chat.id, 'DONE BIDDING')
        # ==Post-Bidding==
        trump = game.currentBid.suit
        game.setTrump(trump)
        deck._setGameRules(game)
        db[message.chat.id]['continueBidding'] = False
        db[message.chat.id]['firstPlayer'] = game.getPlayerOrder(winningBidder)[1]    
        telebot.logging.debug(db[message.chat.id]['remainingPlayers'])
        db[message.chat.id]['remainingPlayers'] = None

        bot.send_message(message.chat.id, f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner}')
        startPlay(message)

    def startPlay(message):
        # ==Playing==
        game = db[message.chat.id]['game']
        deck = db[message.chat.id]['deck']
        user = db[message.chat.id]['player']
        firstPlayer = game.getPlayerOrder(game.currentBidder)[1]
        playerOrder = game.getPlayerOrder(firstPlayer)

        count = 1
        db[message.chat.id]['count'] = count
            
        playerOrder = game.getPlayerOrder(firstPlayer)
        game.setRoundSuit(count)
        game.resetRoundCards()

        for player in playerOrder:
            if isinstance(player, Player):
                playerMessage = ''
                if game.roundSuit:
                    playerMessage += f'Round Suit: {game.roundSuit} || '
                # print('Played Cards: ', end='')
                if game.playedCards:
                    playerMessage += ', '.join([f'{card.owner.name}: {card}' for card in game.playedCards])
                else:
                    playerMessage += 'None'
                bot.send_message(message.chat.id, f'{playerMessage}')

                if player.canFollow(game):
                    player.availableCards = [_ for _ in player.hand if _.suit == game.roundSuit]
                else:
                    if game.roundCount == 1 or (not game.brokeTrump and not game.playedCards):
                        # print('No trump allowed')
                        player.availableCards = [_ for _ in player.hand if _.suit != game.trump]
                    else:
                        player.availableCards = player.hand
                bot.send_message(message.chat.id, f'Your Hand: ', reply_markup=createMarkupPlay(player.availableCards))
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
        text = message.text
        if not db[message.chat.id]['continueBidding']:
            return True
        else:
            return False

    @bot.message_handler(func=lambda message: checkPlay(message))
    def _replyPlay(message):
        # ==Playing==
        game = db[message.chat.id]['game']
        deck = db[message.chat.id]['deck']
        user = db[message.chat.id]['player']
        # firstPlayer = game.getPlayerOrder(game.currentBidder)[1]
        # playerOrder = game.getPlayerOrder(firstPlayer)
        count = db[message.chat.id]['count']

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
            bot.send_message(message.chat.id, f'{text}')
            bot.send_message(message.chat.id, f'{winningCard.owner.name} wins with {winningCard}\n')
            firstPlayer = winningCard.owner
            firstPlayer.tricks += 1
            playerOrder = game.getPlayerOrder(firstPlayer)
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
            bot.send_message(message.chat.id, f'{text}')
            bot.send_message(message.chat.id, f'{winningCard.owner.name} wins with {winningCard}\n')
            firstPlayer = winningCard.owner
            firstPlayer.tricks += 1
            playerOrder = game.getPlayerOrder(firstPlayer)

        db[message.chat.id]['count'] += 1
        count = db[message.chat.id]['count']
        if count > 13:
            bot.send_message(message.chat.id, f'==={game.currentBid} Game Ended===\n{game._results}\n{game._teamResults}', reply_markup=ReplyKeyboardRemove())
        else:
            playerOrder = game.getPlayerOrder(firstPlayer)
            game.setRoundSuit(count)
            game.resetRoundCards()

            for player in playerOrder:
                if isinstance(player, Player):
                    playerMessage = ''
                    if game.roundSuit:
                        playerMessage += f'Round Suit: {game.roundSuit} || '
                    # print('Played Cards: ', end='')
                    if game.playedCards:
                        playerMessage += ', '.join([f'{card.owner.name}: {card}' for card in game.playedCards])
                    else:
                        playerMessage += 'None'
                    bot.send_message(message.chat.id, f'{playerMessage}')

                    if player.canFollow(game):
                        player.availableCards = [_ for _ in player.hand if _.suit == game.roundSuit]
                    else:
                        if game.roundCount == 1 or (not game.brokeTrump and not game.playedCards):
                            # print('No trump allowed')
                            player.availableCards = [_ for _ in player.hand if _.suit != game.trump]
                        else:
                            player.availableCards = player.hand
                    bot.send_message(message.chat.id, f'Your Hand: ', reply_markup=createMarkupPlay(player.availableCards))
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
            KeyboardButton('Pass'), KeyboardButton('More')
        )
        return markup

    def createMarkupPlay(cards):
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
        return markup

    return bot
    
if __name__ == "__main__":
    bot = createBot()