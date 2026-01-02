# Development Status & Roadmap

## Phase 1: Core Features (Study & Stats)
- [x] Environment Setup: Render deployment & LINE Webhook connection.
- [x] DB Connection: Google Sheets API integration (gsheet.py).
- [x] Study Timer: Start/End recording logic.
- [x] Saga Statistics: Deviation & Rank simulation logic (stats.py).
  - Logic: J1 Population=7676, Mean=60min, SD=45min.

## Phase 2: Economy System (Wallet & Shop)
- [x] User Registration: Auto-create account on first interaction.
- [x] Wallet Logic: Add/Subtract EXP with transaction history (economy.py).
- [x] Shop Master: DB schema design complete.
- [x] Shop Implementation:
  - [x] Update economy.py (or create shop.py) to fetch items from DB.
  - [x] Update app.py to display dynamic items.
  - [x] Implement Confirmation Dialog (Confirm Template) to prevent accidental clicks.

## Phase 3: Job Market (Household Chores)
- [x] Job DB: Schema design complete (jobs sheet).
- [x] Job Logic (job.py):
  - [ ] Create Job (Admin only).
  - [x] List OPEN Jobs.
  - [x] Apply for Job (User).
- [x] Job UI: LINE Flex Messages for Job Board.

## Phase 4: Visualization & UX (Future)
- [ ] Rich Menu: Switch menus based on role (Admin/User).
- [ ] Dashboard: Looker Studio integration for Parents.
- [ ] AI Integration: Image recognition for study notes/stopwatch.

## 6. Business Logic Rules
- **EXP Generation**: 1 minute of study = 1 EXP.
- **Transactions**: Direct manipulation of current_exp is forbidden. Must use EconomyService.add_exp() to ensure transactions log is created.
- **Admin Privileges**: Only users with role='ADMIN' can:
  - Approve purchase requests.
  - Create/Delete Jobs.
  - Refund transactions.
