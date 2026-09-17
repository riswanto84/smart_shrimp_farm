# AI OperationalExpense v9

Changes:
- AI OperationalExpense review now has one primary action: Simpan Pengeluaran.
- Saving a complete draft immediately creates the real finance OperationalExpense and redirects to Pengeluaran Operasional.
- Incomplete data is saved back to the draft and remains on the edit/review page.
- Removed the separate operational-expense approval button from the review UI; the legacy approve endpoint remains for compatibility with other AI actions.
- Edit title no longer exposes internal action ID.
- OperationalExpense queryset explicitly reapplies newest-to-oldest ordering after all filters: date DESC, created_at DESC, id DESC.
