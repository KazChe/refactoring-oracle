"""Event ticket refund amounts."""


def refund_amount(ticket, days_before_event):
    amount = 0.0
    if ticket is not None:
        if not ticket["used"]:
            if days_before_event >= 7:
                amount = ticket["price"]
            else:
                if days_before_event >= 1:
                    amount = round(ticket["price"] * 0.5, 2)
                else:
                    amount = 0.0
    return amount


def refund_message(ticket, days_before_event):
    amount = refund_amount(ticket, days_before_event)
    return f"refund ${amount:.2f}" if amount else "no refund"
