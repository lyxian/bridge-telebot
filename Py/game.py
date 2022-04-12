from card import Deck
from user import Bot, Player, Game
from exceptions import IncorrectPlayerCount, InvalidComparison

if __name__ == '__main__':

    # ==Game Start==
    deck = Deck()
    deck._shuffle
    # deck._show
    botNames = ['B', 'C', 'D']
    A = Player('YOU')
    B, C, D = [Bot(name) for name in botNames]
    players = [A, B, C, D]

    # ==Bidding==
    game = Game('spade', players)
    deck._setGameRules(game)
    # cards = deck.deck[:13]
    # testing(cards)

    # ==Playing==
    deck.distribute(players)
    firstPlayer = B

    for _ in range(13):
        playerOrder = game.getPlayerOrder(firstPlayer)
        game.setRoundSuit()
        plays = {}

        for player in playerOrder:
            if player == A:
                if game.roundSuit:
                    print(f'Round Suit: {game.roundSuit} || ', end='')
                print('Played Cards: ', end='')
                print(*[f'{player.name}: {card}' for card, player in plays.items()], sep=', ')
            playedCard = player.play(game)
            plays[playedCard] = player
            if game.roundSuit is None:
                game.setRoundSuit(playedCard.suit)
                deck._setRoundRules(game)

        winningCard = sorted(plays.keys())[-1]
        print(*[f'{player.name}: {card}' for card, player in plays.items()], sep=' | ')
        print(f'{plays[winningCard].name} wins with {winningCard}\n')
        firstPlayer = plays[winningCard]
        firstPlayer.tricks += 1
    
    print(f'===Game Ended===\n{game._results}')
