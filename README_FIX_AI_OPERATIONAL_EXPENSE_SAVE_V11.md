# Fix AI OperationalExpense v11

- Save on the review page creates the real `finance.OperationalExpense`.
- Evidence-copy errors no longer roll back the financial transaction.
- AI action is marked executed only after the transaction is created.
- Duplicate unreachable render code removed.
- Sorting remains newest date first in `finance.views._expense_queryset`.
- No database migration is required.
