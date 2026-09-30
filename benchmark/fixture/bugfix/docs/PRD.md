# Back-office fixes — the owner's list

Seven defects reported by the finance team against the back office in `app/`. Each is small; fix them
all. Nothing new is being built.

- **B1** — `billing.total()` ignores the discount when the quantity is zero; a zero-quantity line with
  a discount must still show the discount as a negative line.
- **B2** — `billing.total()` rounds half-down; the finance rule is half-up to the cent.
- **B3** — `billing.invoice_number()` pads to 5 digits; invoices need 6 (`INV-000123`).
- **B4** — `notify.email_subject()` strips accents (`Fatura atrasada` becomes `Fatura atrasada` but
  `Cobrança` becomes `Cobranca`); subjects must keep them.
- **B5** — `notify.sms_text()` sends texts longer than 160 characters; they must be cut at 157 with `...`.
- **B6** — overdue invoices must notify the customer, through `notify`. Which channel — e-mail, SMS or
  both — was never decided.
- **B7** — `reports.csv_export()` separates columns with `;`; the accounting tool expects `,`.
