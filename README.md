# Credit Card Tracker

A web app for keeping track of credit cards, spending, and payment due dates. Each user gets their own account and only sees their own data.

**Live demo:** https://deeksha-card-tracker.streamlit.app

> This is a portfolio project. Please use fake card details and a throwaway password when you try it.

## Screenshots

![Dashboard](screenshots/dashboard.png)
![Cards and transactions](screenshots/transactions.png)
![Login](screenshots/login.png)

## What it does

- Sign up and log in with a username and password
- Add cards with a nickname, last 4 digits, credit limit, and due date
- Log transactions by card, category, amount, and date
- See spending by category in a chart
- See credit utilization per card, with a warning above 30%
- Get due-date alerts (red for 3 days or less, yellow for 7 days or less)

## Built with

- Python and Streamlit for the app
- pandas for the analysis behind the dashboard
- PostgreSQL on Supabase for permanent storage
- SQLAlchemy for talking to the database
- bcrypt for password hashing
- Streamlit Community Cloud for hosting

## How it works

Passwords are never stored as plain text. They are hashed with bcrypt, and every database query is filtered by the logged-in user's ID, so one user can't see another user's cards or transactions. Only the last 4 digits of a card are stored, never the full number. The database connection string lives in Streamlit secrets and is not in this repo.

## Run it locally

1. Clone the repo and open the folder.
2. Create and activate a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install the requirements:
   ```
   pip install -r requirements.txt
   ```
4. Create a free Supabase project and copy its session pooler connection string.
5. Create `.streamlit/secrets.toml` with:
   ```toml
   [db]
   url = "postgresql+psycopg2://USER:PASSWORD@HOST:5432/postgres"
   ```
6. Start the app:
   ```
   streamlit run app.py
   ```

## Limitations

There is no password reset, email verification, or lockout after repeated failed logins. That is fine for a demo, but it would need to be added before real use.

## Possible next steps

- CSV export of transactions
- Monthly spending trend chart
- Password reset by email

Built by Deeksha.