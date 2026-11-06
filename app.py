import sqlite3
import pandas as pd
import streamlit as st

conn = sqlite3.connect("cards.db", check_same_thread=False)
conn.execute("""
CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nickname TEXT NOT NULL,
    last4 TEXT NOT NULL,
    credit_limit REAL NOT NULL,
    due_day INTEGER NOT NULL
)
""")
conn.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    txn_date TEXT NOT NULL,
    FOREIGN KEY (card_id) REFERENCES cards(id)
)
""")
conn.commit()

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
        conn.execute(
            "INSERT INTO cards (nickname, last4, credit_limit, due_day) VALUES (?, ?, ?, ?)",
            (nickname, last4, limit, int(due_day)),
        )
        conn.commit()
        st.success("Card added!")
    else:
        st.error("Enter a nickname and exactly 4 digits.")

st.subheader("Your cards")
cards_df = pd.read_sql("SELECT id, nickname, last4, credit_limit, due_day FROM cards", conn)
st.dataframe(cards_df.drop(columns="id"), width="stretch")

# ---------- Add transaction ----------
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
            conn.execute(
                "INSERT INTO transactions (card_id, amount, category, txn_date) VALUES (?, ?, ?, ?)",
                (options[card_label], amount, category, str(txn_date)),
            )
            conn.commit()
            st.success("Transaction added!")
        else:
            st.error("Amount must be more than 0.")

    txns = pd.read_sql(
        """
        SELECT t.txn_date AS date, c.nickname AS card, t.category, t.amount
        FROM transactions t JOIN cards c ON c.id = t.card_id
        ORDER BY t.txn_date DESC
        """,
        conn,
    )
    st.dataframe(txns, width="stretch")

# ---------- Dashboard ----------
st.header("Dashboard")
all_txns = pd.read_sql(
    """
    SELECT c.nickname AS card, t.category, t.amount
    FROM transactions t JOIN cards c ON c.id = t.card_id
    """,
    conn,
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