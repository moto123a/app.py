import streamlit as st
import sqlite3
from datetime import datetime
from forex_python.converter import CurrencyRates
from num2words import num2words

# ========== DB SETUP ==========
conn = sqlite3.connect('finance_goals.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    amount REAL,
    currency TEXT,
    years REAL
)''')
c.execute('''CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id INTEGER,
    date TEXT,
    usd_sent REAL,
    inr_equiv REAL
)''')
conn.commit()

# ========== EXCHANGE RATE ==========
c_rates = CurrencyRates()
try:
    exchange_rate = c_rates.get_rate('USD', 'INR')
except:
    exchange_rate = 83.0

# ========== SELECT GOAL ==========
st.sidebar.header("🎯 Your Financial Goals")
c.execute("SELECT id, title FROM goals")
goals = c.fetchall()
goal_titles = [f"{g[1]} (ID: {g[0]})" for g in goals]
goal_ids = [g[0] for g in goals]

selected_goal_index = st.sidebar.selectbox("Select a Goal", list(range(len(goal_titles))), format_func=lambda i: goal_titles[i]) if goals else None
selected_goal_id = goal_ids[selected_goal_index] if selected_goal_index is not None else None

# ========== CREATE NEW GOAL ==========
st.sidebar.markdown("---")
st.sidebar.subheader("➕ Create New Goal")
with st.sidebar.form("new_goal_form"):
    new_title = st.text_input("Title (e.g., 'Loan', 'Buy a Car')")
    new_amount = st.number_input("Target Amount", min_value=0.0, step=1000.0, format="%.2f")
    new_currency = st.radio("Currency", ["INR", "USD"])
    new_years = st.number_input("Payoff Duration (Years)", min_value=0.1, step=0.1, format="%.1f")
    create_goal = st.form_submit_button("Create Goal")

if create_goal and new_title:
    final_amount = new_amount * exchange_rate if new_currency == "USD" else new_amount
    c.execute("INSERT INTO goals (title, amount, currency, years) VALUES (?, ?, ?, ?)",
              (new_title, final_amount, "INR", new_years))
    conn.commit()
    st.success("🎉 New goal created! Refresh the page to see it in the list.")

# ========== SHOW SELECTED GOAL ==========
if selected_goal_id:
    c.execute("SELECT title, amount, years FROM goals WHERE id = ?", (selected_goal_id,))
    goal = c.fetchone()
    title, amount_inr, years = goal

    st.title(f"📌 {title} Tracker")
    loan_words = num2words(round(amount_inr), lang='en_IN').title()
    st.caption(f"Target: ₹{amount_inr:,.0f} ({loan_words} Rupees)")

    # Calculations
    days = int(years * 365)
    weeks = int(years * 52)
    months = int(years * 12)

    daily_inr = amount_inr / days
    weekly_inr = amount_inr / weeks
    monthly_inr = amount_inr / months
    yearly_inr = amount_inr / years

    daily_usd = daily_inr / exchange_rate
    weekly_usd = weekly_inr / exchange_rate
    monthly_usd = monthly_inr / exchange_rate
    yearly_usd = yearly_inr / exchange_rate

    st.metric("Daily Send Target", f"${daily_usd:,.2f} → ₹{daily_inr:,.0f} ({days} days)")
    st.metric("Weekly Send Target", f"${weekly_usd:,.2f} → ₹{weekly_inr:,.0f} ({weeks} weeks)")
    st.metric("Monthly Send Target", f"${monthly_usd:,.2f} → ₹{monthly_inr:,.0f} ({months} months)")
    st.metric("Yearly Total (USD)", f"${yearly_usd:,.2f} → ₹{yearly_inr:,.0f} ({years:.1f} years)")

    # Log Payment
    st.subheader("💵 Log a Payment")
    with st.form("payment_form"):
        usd_sent = st.number_input("USD Sent", min_value=0.0, step=1.0)
        pay_date = st.date_input("Date", value=datetime.today())
        submitted = st.form_submit_button("Log Payment")

        if submitted:
            inr_equiv = usd_sent * exchange_rate
            c.execute("INSERT INTO payments (goal_id, date, usd_sent, inr_equiv) VALUES (?, ?, ?, ?)",
                      (selected_goal_id, pay_date.strftime("%Y-%m-%d"), usd_sent, inr_equiv))
            conn.commit()
            st.success("✅ Payment logged!")

    # Progress
    st.subheader("📊 Progress")
    c.execute("SELECT usd_sent, inr_equiv FROM payments WHERE goal_id = ?", (selected_goal_id,))
    payments = c.fetchall()
    paid_inr = sum([p[1] for p in payments])
    remaining = amount_inr - paid_inr
    percent = (paid_inr / amount_inr) * 100 if amount_inr > 0 else 0

    st.progress(min(percent / 100, 1.0))
    st.write(f"**Paid:** ₹{paid_inr:,.0f} / ₹{amount_inr:,.0f} ({percent:.2f}%)")
    st.write(f"**Remaining:** ₹{remaining:,.0f}")

    # Daily Reminder with optional manual override
    st.subheader("📅 Custom Earning Targets")
    use_custom_target = st.checkbox("✏️ Set custom earning targets")
    if use_custom_target:
        custom_input = st.selectbox("Which one do you want to enter?", ["Daily", "Weekly", "Monthly", "Yearly"])
        input_usd = st.number_input(f"Enter your {custom_input} USD Goal", min_value=0.0, step=1.0)

        if custom_input == "Daily":
            daily_usd = input_usd
            weekly_usd = daily_usd * 7
            monthly_usd = daily_usd * 30
            yearly_usd = daily_usd * 365
        elif custom_input == "Weekly":
            weekly_usd = input_usd
            daily_usd = weekly_usd / 7
            monthly_usd = daily_usd * 30
            yearly_usd = daily_usd * 365
        elif custom_input == "Monthly":
            monthly_usd = input_usd
            daily_usd = monthly_usd / 30
            weekly_usd = daily_usd * 7
            yearly_usd = daily_usd * 365
        else:
            yearly_usd = input_usd
            daily_usd = yearly_usd / 365
            weekly_usd = daily_usd * 7
            monthly_usd = daily_usd * 30

        st.metric("Daily", f"${daily_usd:,.2f} → ₹{daily_usd * exchange_rate:,.0f} ({days} days)")
        st.metric("Weekly", f"${weekly_usd:,.2f} → ₹{weekly_usd * exchange_rate:,.0f} ({weeks} weeks)")
        st.metric("Monthly", f"${monthly_usd:,.2f} → ₹{monthly_usd * exchange_rate:,.0f} ({months} months)")
        st.metric("Yearly", f"${yearly_usd:,.2f} → ₹{yearly_usd * exchange_rate:,.0f} ({years:.1f} years)")
    else:
        daily_needed_inr = remaining / days if days > 0 else 0
        daily_needed_usd = daily_needed_inr / exchange_rate if exchange_rate > 0 else 0

        weekly_needed_inr = remaining / weeks if weeks > 0 else 0
        weekly_needed_usd = weekly_needed_inr / exchange_rate if exchange_rate > 0 else 0

        monthly_needed_inr = remaining / months if months > 0 else 0
        monthly_needed_usd = monthly_needed_inr / exchange_rate if exchange_rate > 0 else 0

        yearly_needed_usd = remaining / exchange_rate / years if years > 0 else 0

        st.metric("Daily Goal", f"${daily_needed_usd:,.2f} → ₹{daily_needed_inr:,.0f} ({days} days)")
        st.metric("Weekly Goal", f"${weekly_needed_usd:,.2f} → ₹{weekly_needed_inr:,.0f} ({weeks} weeks)")
        st.metric("Monthly Goal", f"${monthly_needed_usd:,.2f} → ₹{monthly_needed_inr:,.0f} ({months} months)")
        st.metric("Yearly Goal", f"${yearly_needed_usd:,.2f} → ₹{remaining:,.0f} ({years:.1f} years)")
        st.caption("“Keep going — every ₹ counts!”")
else:
    st.warning("No goal selected. Please create or select one from the sidebar.")
