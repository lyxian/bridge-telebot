# bridge-telebot

- Features :
  - game mechanics
    - game phases :
      - card distribution
        - deck
        - card
        - determine hand strength
      - player management
        - init players
        - customize player
      - bidding
        - deciding strong suite
        - choosing partner
        - re-shuffling
      - game round
        - deciding to win/lose round (bot)
        - breaking trump
      - game end
        - end of 13 rounds
        - required sets won
  - AI programming

# Development

**v1** (working)

1. card distribution
2. init players
3. deck (ok)
4. card (ok)
5. end of 13 rounds

**v1b** (ongoing)

1. bidding (ok)
2. required sets won (ok) (!stop early)
3. deciding to win/lose round (bot)
4. determine hand strength (ok)

# AI Programming

**Bidding**

- suit
  - check strongest long running suit of at least 4
  - check increase in strength with next best card
  - skip if favorable
    - same suit
    - has at least 4 points in bidded suit
- tricks
  - strength / 4
  - remainder / 4 = % to go +1

**Playing**
.

##Packages (list required packages & run .scripts/python-pip.sh)

##Packages
