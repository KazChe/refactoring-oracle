"""Loyalty points ledger."""

POINTS_PER_DOLLAR = 2


def _points_for(amount):
    return int(amount) * POINTS_PER_DOLLAR


class Ledger:
    def __init__(self):
        self.balance = 0
        self.history = []

    def purchase(self, amount):
        earned = _points_for(amount)
        self.balance += earned
        self.history.append(("earn", earned))
        return earned

    def redeem(self, points):
        if points > self.balance:
            raise ValueError("insufficient points")
        self.balance -= points
        self.history.append(("redeem", points))
        return self.balance
