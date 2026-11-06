from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text


@st.cache_resource
def get_engine():
    return create_engine(st.secrets["db"]["url"], pool_pre_ping=True)


engine = get_engine()

with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS cards (
            id SERIAL PRIMARY KEY,
            nickname TEXT NOT NULL,
            last4 TEXT NOT NULL,
            credit_limit DOUBLE PRECISION NOT NULL,
            due_day INTEGER NOT NULL
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            card_id INTEGER NOT NULL REFERENCES cards(id),
            amount DOUBLE PRECISION NOT NULL,
            category TEXT NOT NULL,
            txn_date TEXT NOT NULL
        )
    """))


def query(sql):
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


st.title("Credit Card Tracker")

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
                text("INSERT INTO cards (nickname, last4, credit_limit, due_day) "
                     "VALUES (:n, :l, :c, :d)"),
                {"n": nickname, "l": last4, "c": float(limit), "d": int(due_day)},
            )
        st.success("Card added!")
    else:
        st.error("Enter a nickname and exactly 4 digits.")

st.subheader("Your cards")
cards_df = query("SELECT id, nickname, last4, credit_limit, due_day FROM cards ORDER BY id")
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

    txns = query("""
        SELECT t.txn_date AS date, c.nickname AS card, t.category, t.amount
        FROM transactions t JOIN cards c ON c.id = t.card_id
        ORDER BY t.txn_date DESC
    """)
    st.dataframe(txns, width="stretch")

# ---------- Dashboard ----------
st.header("Dashboard")
all_txns = query("""
    SELECT c.nickname AS card, t.category, t.amount
    FROM transactions t JOIN cards c ON c.id = t.card_id
""")

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