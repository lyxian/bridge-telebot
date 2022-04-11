from enum import Enum

class Rank(Enum):
    two = 1
    three = 2
    four = 3
    five = 4
    six = 5
    seven = 6
    eight = 7
    nine = 8
    ten = 9
    jack = 10
    queen = 11
    king = 12
    ace = 13

class Suit(Enum):
    club = 1
    diamond = 2
    heart = 3
    spade = 4

cardMappings = {
    'ace': 'A',
    'two': '2',
    'three': '3',
    'four': '4',
    'five': '5',
    'six': '6',
    'seven': '7',
    'eight': '8',
    'nine': '9',
    'ten': '10',
    'jack': 'J',
    'queen': 'Q',
    'king': 'K',
    'club': '♣',
    'diamond': '♦',
    'heart': '♥',
    'spade': '♠'
}