"""Reports for the accounting tool."""


def csv_export(rows):
    return "\n".join(";".join(str(c) for c in r) for r in rows)
