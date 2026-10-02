# SimpleBank

REST API of a small bank: registration, an account with a welcome bonus, transaction history, and transfers between clients with a fee.

**Stack:** Python 3.13, Django 6.1, Django REST Framework, SimpleJWT, PostgreSQL 17, pytest, Docker.

## Running

### With Docker

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`. Migrations are applied when the container starts. A `.env` file is optional: every setting has a default.

### Locally

The database runs in Docker, Django runs on the host.

```bash
cp .env.example .env
docker compose -f docker-compose.local.yml up -d
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Tests

```bash
docker compose exec api pytest      # in Docker
pytest                              # locally
```

The tests go from the HTTP layer down to the database and cover registration, login, balance, history with date filtering, transfers, rollback on failure, and concurrent transfers.

## API

All paths start with `/api/v1`. Protected endpoints require the `Authorization: Bearer <access>` header.

| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `/auth/register/` | public | Register with email and password |
| POST | `/auth/token/` | public | Log in, returns `access` and `refresh` |
| POST | `/auth/token/refresh/` | public | New `access` token from a `refresh` token |
| GET | `/account/` | token | Account number and current balance |
| GET | `/transactions/` | token | Transaction history |
| GET | `/transactions/<id>/` | token | A single transaction |
| POST | `/transfers/` | token | Transfer to another client's account |

**Registration**

```bash
curl -X POST localhost:8000/api/v1/auth/register/ \
  -H 'Content-Type: application/json' \
  -d '{"email": "user@example.com", "password": "Str0ng-Passw0rd!"}'
```

Registration creates an account with a unique 10-digit number and credits it with €10,000.

**Balance**

```json
{"account_number": "2850075008", "balance": "10000.00", "currency": "EUR"}
```

**Transaction history**

`GET /transactions/?from=2026-09-01&to=2026-09-28` — both parameters are optional, both bounds are inclusive. The response is paginated: `page`, `page_size` (20 by default, 100 at most).

```json
{
  "id": "7424c371-...",
  "amount": "100.00",
  "type": "debit",
  "category": "transfer",
  "timestamp": "2026-10-02T12:36:27.831053Z",
  "transfer_id": "73b1..."
}
```

`type` is `credit` or `debit`; `category` is `welcome_bonus`, `transfer` or `fee`.

**Transfer**

```bash
curl -X POST localhost:8000/api/v1/transfers/ \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"receiver_account_number": "0254458614", "amount": "100.00"}'
```

```json
{"id": "...", "amount": "100.00", "fee": "5.00", "status": "SUCCESS", "type": "debit", "created_at": "..."}
```

**Error codes:** 400 — invalid data or insufficient funds; 401 — missing or invalid token; 404 — receiver account not found; 429 — rate limit exceeded.

## Commands

| Command | What it does |
|---|---|
| `python manage.py new_users` | Creates four demo clients with accounts and the welcome bonus; prints their account numbers and password. Running it again creates no duplicates |
| `python manage.py check_balance_after_transaction` | Compares each account balance with the sum of its ledger entries; exits with an error on a mismatch |
| `make run` / `make mi` / `make mm` | Start the server, apply migrations, create migrations |

In Docker, run them through `docker compose exec api ...`.

## Architecture

The code is split into apps: `users` (authentication), `clients` (bank client and registration), `accounts` (accounts), `transactions` (transfers and the ledger), `common` (shared models, logging). Views only deal with HTTP; business logic lives in services.

### Ledger

- **A ledger entry** is an immutable row with a signed amount: positive for a credit, negative for a debit. The transaction history in the API is built from these entries.
- **The account balance** is a stored value that changes in the same database transaction as the ledger entries. At any moment the balance equals the sum of the account's entries; the reconciliation command and a dedicated test verify this.
- **A transfer** creates one record of the operation itself and three ledger entries: the amount debit and the fee debit for the sender, and the amount credit for the receiver.
- **The welcome bonus** is also a ledger entry, so an account's history starts with its first operation rather than with money that appeared from nowhere.

### Atomic transfers

- The whole transfer runs in a single database transaction: on any error neither balances nor history change.
- Both accounts are locked with `SELECT ... FOR UPDATE` before the balance check, so two concurrent transfers cannot spend the same money.
- Locks are taken in a fixed order (by account id), so opposite transfers A→B and B→A do not deadlock.
- Amounts are stored as `Decimal` with two decimal places; a non-negative balance and the account number format are additionally enforced by database constraints.

### Logging

- Every request gets a `trace_id`. If the client sends an `X-Request-ID` header, that value is used; the id is returned in the same response header.
- The `trace_id` and the user id are added to every log line automatically, so a single value finds all events of one request.
- Services log what they started and how it ended; every rejection includes its reason. All 4xx responses are logged in one place together with the message the client received.
- Emails are masked in logs; passwords and tokens are never written.

```
INFO    trace=ee41... user=bbb3... transactions.transfer_service Transfer started sender_account_id=... amount=50000.00
WARNING trace=ee41... user=bbb3... transactions.transfer_service Transfer rejected: insufficient funds required=51250.00 available=9895.00
INFO    trace=ee41... user=bbb3... simple_bank.request POST /api/v1/transfers/ -> 400 in 11.3ms
```

## Assumptions and limitations

**Assumptions**

- The fee is 2.5% of the amount but not less than €5, rounded to the cent. It is charged to the sender on top of the transfer amount: a €100 transfer debits €105 and the receiver gets €100.
- The fee appears in the sender's history as a separate entry instead of being included in the transfer amount.
- The task does not define where the fee goes, so a bank-owned account is not modelled: the fee is only debited from the client.

**Limitations**

- A single currency (EUR) and one account per client.
- The maximum amount of one transfer is €500,000.
- Transfers have no idempotency key: a repeated request creates a second transfer.
- Rate limits: registration — 5 per hour, login — 10 per minute, token refresh — 30 per minute per IP. Counters are kept in process memory, so with several workers each one counts its own limit.
- The `access` token lives for 15 minutes, the `refresh` token for 1 day.
- Date filtering works in UTC.
- Settings are meant for a demo: `ALLOWED_HOSTS = ['*']`, the secret key in `docker-compose.yml` has a default value, and admin static files are not served.
