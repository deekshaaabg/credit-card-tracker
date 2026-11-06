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
conn.commit()

st.title("Credit Card Tracker")

with st.form("add_card", clear_on_submit=True):
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
df = pd.read_sql("SELECT nickname, last4, credit_limit, due_day FROM cards", conn)
st.dataframe(df, width="stretch")