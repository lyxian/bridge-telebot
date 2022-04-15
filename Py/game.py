from card import Deck, Rank, Suit
from user import Bot, Player, Game
from exceptions import IncorrectPlayerCount, InvalidComparison

def play(game, firstPlayer):
    for _ in range(13):
        playerOrder = game.getPlayerOrder(firstPlayer)
        game.setRoundSuit()
        game.resetRoundCards()

        for player in playerOrder:
            if isinstance(player, Player):
                if game.roundSuit:
                    print(f'Round Suit: {game.roundSuit} || ', end='')
                print('Played Cards: ', end='')
                if game.playedCards:
                    print(*[f'{card.owner.name}: {card}' for card in game.playedCards], sep=', ')
                else:
                    print('None')
            playedCard = player.play(game)
            game.addRoundCards(playedCard)
            if game.roundSuit is None:
                game.setRoundSuit(playedCard.suit)
                deck._setRoundRules(game)

        winningCard = sorted(game.playedCards, reverse=True)[0]
        print(*[f'{card.owner.name}: {card}' for card in game.playedCards], sep=' | ')
        print(f'{winningCard.owner.name} wins with {winningCard}\n')
        firstPlayer = winningCard.owner
        firstPlayer.tricks += 1
    
    print(f'==={game.currentBid} Game Ended===\n{game._results}\n{game._teamResults}')

def bidding():
    pass

# ==Game Start==
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
print([i.name for i in playerOrder])

import time
continueBidding = True
while continueBidding:
    skippedPlayers = []
    print(f'Round bidders: {[i.name for i in playerOrder]}')
    for player in playerOrder:
        if game.currentBidder and game.currentBidder == player:
            continueBidding = False
            winningBidder = player
            game.askPlayer(player)
            break
        bid = player.bid(game)
        if bid == 'pass':
            skippedPlayers.append(player)
            print(f'{player.name} passed\n')
        else:
            game.currentBid = bid
            game.currentBidder = player
            print(f'Current bid by {player.name} is: {bid}\n')
        
    if skippedPlayers:
        for player in skippedPlayers:
            playerOrder.pop(playerOrder.index(player))
    time.sleep(1)
    

# ==Post-Bidding==
if game.currentBid is None:
    trump = 'spade'
    winningBidder = firstPlayer
    winningBidder.likelyPartner = firstPlayer
else:
    trump = game.currentBid.suit
game.setTrump(trump)
deck._setGameRules(game)

if winningBidder.likelyPartner.owner == A:
    print(f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner} (YOU)')
else:
    print(f'\nFinal Bid by {winningBidder.name}: {game.currentBid}, Partner = {winningBidder.likelyPartner}')

# ==Playing==
firstPlayer = game.getPlayerOrder(winningBidder)[1]

# ! Check for re-shuffle

if __name__ == '__main__':
    play(game, firstPlayer)
    # A._show
    # print(Deck.showStrength(A.hand))
    # print(Deck.showSuitStrength(A.hand))
    # print(A._bestSuit, B._bestSuit, C._bestSuit, D._bestSuit)

    # print(Deck.showSuitStrength(A.hand), Deck.showStrength(A.hand), '\n', Deck.showBySuitStr(A.hand))
    # print()
    # print(Deck.showSuitStrength(B.hand), Deck.showStrength(B.hand), '\n', Deck.showBySuitStr(B.hand))
    # print()
    # print(Deck.showSuitStrength(C.hand), Deck.showStrength(C.hand), '\n', Deck.showBySuitStr(C.hand))
    # print()
    # print(Deck.showSuitStrength(D.hand), Deck.showStrength(D.hand), '\n', Deck.showBySuitStr(D.hand))
    # print()