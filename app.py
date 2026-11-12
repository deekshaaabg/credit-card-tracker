from datetime import date

import bcrypt
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

st.set_page_config(page_title="Credit Card Tracker", page_icon="💳", layout="centered")

st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
[data-testid="stForm"] {
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 1.5rem;
    background: rgba(255,255,255,0.03);
}
[data-testid="stFormSubmitButton"] button {
    width: 100%;
    border-radius: 10px;
    font-weight: 600;
    padding: 0.6rem 0;
}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_engine():
    return create_engine(st.secrets["db"]["url"], pool_pre_ping=True)


engine = get_engine()

with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS cards (
            id SERIAL PRIMARY KEY,
            nickname TEXT NOT NULL,
            last4 TEXT NOT NULL,
            credit_limit DOUBLE PRECISION NOT NULL,
            due_day INTEGER NOT NULL
        )
    """))
    conn.execute(text(
        "ALTER TABLE cards ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)"
    ))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            card_id INTEGER NOT NULL REFERENCES cards(id),
            amount DOUBLE PRECISION NOT NULL,
            category TEXT NOT NULL,
            txn_date TEXT NOT NULL
        )
    """))


def query(sql, params=None):
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def sign_up(username, password):
    if len(username) < 3 or len(password) < 8:
        return "Username needs 3+ characters and password needs 8+."
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO users (username, password_hash) VALUES (:u, :p)"),
                {"u": username.strip().lower(), "p": hashed},
            )
        return None
    except IntegrityError:
        return "That username is already taken."


def log_in(username, password):
    df = query(
        "SELECT id, username, password_hash FROM users WHERE username = :u",
        {"u": username.strip().lower()},
    )
    if df.empty:
        return None
    row = df.iloc[0]
    if bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        return {"id": int(row["id"]), "username": row["username"]}
    return None


# ---------- Login / Sign up ----------
if "user" not in st.session_state:
    st.markdown("""
    <style>
    .block-container {max-width: 520px; padding-top: 3rem;}
    .hero {text-align: center; margin-bottom: 1rem;}
    .hero .icon {font-size: 3.2rem;}
    .hero h1 {
        background: linear-gradient(90deg, #7C5CFF, #00C6FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        margin: 0.2rem 0;
        padding: 0;
    }
    .hero p {color: #9AA4B2; margin: 0;}
    .chips {display: flex; justify-content: center; gap: 0.5rem; flex-wrap: wrap; margin: 1rem 0 1.5rem;}
    .chip {
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        background: rgba(124,92,255,0.15);
        color: #C9BFFF;
        font-size: 0.8rem;
    }
    </style>
    <div class="hero">
        <div class="icon">💳</div>
        <h1>Credit Card Tracker</h1>
        <p>Track spending, utilization and due dates in one place.</p>
    </div>
    <div class="chips">
        <span class="chip">📊 Spending charts</span>
        <span class="chip">💳 Utilization alerts</span>
        <span class="chip">🗓️ Due dates</span>
    </div>
    """, unsafe_allow_html=True)

    login_tab, signup_tab = st.tabs(["🔑 Log in", "✨ Sign up"])

    with login_tab:
        with st.form("login"):
            u = st.text_input("Username", placeholder="your username")
            p = st.text_input("Password", type="password", placeholder="••••••••")
            login_clicked = st.form_submit_button("Log in")
        if login_clicked:
            found = log_in(u, p)
            if found:
                st.session_state.user = found
                st.rerun()
            else:
                st.error("Wrong username or password.")

    with signup_tab:
        with st.form("signup"):
            new_u = st.text_input("Choose a username", placeholder="at least 3 characters")
            new_p = st.text_input("Choose a password", type="password", placeholder="at least 8 characters")
            new_p2 = st.text_input("Confirm password", type="password", placeholder="repeat the password")
            signup_clicked = st.form_submit_button("Create account")
        if signup_clicked:
            if new_p != new_p2:
                st.error("Passwords don't match.")
            else:
                problem = sign_up(new_u, new_p)
                if problem:
                    st.error(problem)
                else:
                    st.success("Account created! Go to the Log in tab.")

    st.caption("Demo project: please use fake card data and a throwaway password.")
    st.stop()

# ---------- Logged-in app ----------
st.title("💳 Credit Card Tracker")

user = st.session_state.user
uid = user["id"]

st.sidebar.write(f"Logged in as **{user['username']}**")
if st.sidebar.button("Log out"):
    st.session_state.clear()
    st.rerun()

# ---------- Add card ----------
with st.form("add_card", clear_on_submit=True):
    st.subheader("Add a card")
    nickname = st.text_input("Card nickname (e.g. HDFC Regalia)")
    last4 = st.text_input("Last 4 digits only", max_chars=4)
    limit = st.number_input("Credit limit (₹)", min_value=0.0, step=1000.0)
    due_day = st.number_input("Due day of month", min_value=1, max_value=31, value=5)
    submitted = st.form_submit_button("Add card")

if submitted:
    if nickname and last4.isdigit() and len(last4) == 4:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO cards (nickname, last4, credit_limit, due_day, user_id) "
                     "VALUES (:n, :l, :c, :d, :uid)"),
                {"n": nickname, "l": last4, "c": float(limit),
                 "d": int(due_day), "uid": uid},
            )
        st.success("Card added!")
    else:
        st.error("Enter a nickname and exactly 4 digits.")

st.subheader("Your cards")
cards_df = query(
    "SELECT id, nickname, last4, credit_limit, due_day FROM cards "
    "WHERE user_id = :uid ORDER BY id",
    {"uid": uid},
)
st.dataframe(cards_df.drop(columns="id"), width="stretch")

# ---------- Transactions ----------
st.header("Transactions")
if cards_df.empty:
    st.info("Add a card first.")
else:
    options = {f"{r.nickname} (••{r.last4})": int(r.id) for r in cards_df.itertuples()}
    with st.form("add_txn", clear_on_submit=True):
        card_label = st.selectbox("Card", list(options.keys()))
        amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0)
        category = st.selectbox(
            "Category", ["Food", "Shopping", "Travel", "Bills", "Fuel", "Entertainment", "Other"]
        )
        txn_date = st.date_input("Date")
        txn_submitted = st.form_submit_button("Add transaction")

    if txn_submitted:
        if amount > 0:
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO transactions (card_id, amount, category, txn_date) "
                         "VALUES (:cid, :a, :cat, :d)"),
                    {"cid": options[card_label], "a": float(amount),
                     "cat": category, "d": str(txn_date)},
                )
            st.success("Transaction added!")
        else:
            st.error("Amount must be more than 0.")

    txns = query(
        """
        SELECT t.txn_date AS date, c.nickname AS card, t.category, t.amount
        FROM transactions t JOIN cards c ON c.id = t.card_id
        WHERE c.user_id = :uid
        ORDER BY t.txn_date DESC
        """,
        {"uid": uid},
    )
    st.dataframe(txns, width="stretch")

# ---------- Dashboard ----------
st.header("Dashboard")
all_txns = query(
    """
    SELECT c.nickname AS card, t.category, t.amount
    FROM transactions t JOIN cards c ON c.id = t.card_id
    WHERE c.user_id = :uid
    """,
    {"uid": uid},
)

if all_txns.empty:
    st.info("Add some transactions to see charts.")
else:
    st.subheader("Spending by category")
    st.bar_chart(all_txns.groupby("category")["amount"].sum())

    st.subheader("Credit utilization")
    spent = all_txns.groupby("card")["amount"].sum().rename("spent")
    util = cards_df.set_index("nickname")[["credit_limit"]].join(spent).fillna(0)
    util["utilization_%"] = (
        util["spent"] / util["credit_limit"].replace(0, float("nan")) * 100
    ).round(1)
    st.dataframe(util, width="stretch")

    for name, row in util.iterrows():
        if row["utilization_%"] > 30:
            st.warning(f"{name} is at {row['utilization_%']}% utilization. Keep it under 30%.")

# ---------- Due date alerts ----------
st.header("Upcoming payments")
today = date.today()

if cards_df.empty:
    st.info("Add a card to see due dates.")
else:
    for row in cards_df.itertuples():
        due_day = min(row.due_day, 28)
        due = date(today.year, today.month, due_day)
        if due < today:
            month = today.month % 12 + 1
            year = today.year + (1 if today.month == 12 else 0)
            due = date(year, month, due_day)
        days_left = (due - today).days
        label = f"{row.nickname} (••{row.last4}): due on {due.strftime('%d %b')} ({days_left} days left)"
        if days_left <= 3:
            st.error(label)
        elif days_left <= 7:
            st.warning(label)
        else:
            st.info(label)