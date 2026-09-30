"""Billing: invoice totals and numbering."""


def total(lines, discount_cents=0):
    """Sum of qty * unit_cents over the lines, minus the discount (skipped when all quantities are 0)."""
    gross = sum(l["qty"] * l["unit_cents"] for l in lines)
    if any(l["qty"] for l in lines):
        gross -= discount_cents
    return int(gross)


def invoice_number(n):
    return "INV-%05d" % n
