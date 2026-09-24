"""Event ticket refund amounts."""


def refund_amount(ticket, days_before_event):
    if ticket is None:
        return 0.0
    if ticket["used"]:
        return 0.0
    if days_before_event >= 7:
        return ticket["price"]
    if days_before_event >= 1:
        return round(ticket["price"] * 0.5, 2)
    return 0.0


def refund_message(ticket, days_before_event):
    amount = refund_amount(ticket, days_before_event)
    return f"refund ${amount:.2f}" if amount else "no refund"
