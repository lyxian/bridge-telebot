class IncorrectPlayerCount(Exception):
    """Exception raised when number of playes is not equals to four."""
    def __init__(self):
        super().__init__("Number of players is not equals to four")

class InvalidComparison(Exception):
    """Exception raised when program failed to compare order of two cards"""
    def __init__(self, x, y):
        super().__init__(f"Program failed to compare order of two cards: {x.strip()}, {y.strip()}")

class CannotFindLikelyPartner(Exception):
    """Exception raised when program failed to find likely partner from set of cards"""
    def __init__(self):
        super().__init__(f"Program failed to find likely partner from set of cards")

class ImprobableHand(Exception):
    """Exception raised when program failed to find likely partner from improbable hand"""
    def __init__(self):
        super().__init__(f"Program failed to find likely partner from improbable hand")
