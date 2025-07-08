import streamlit as st
import sqlite3
from datetime import datetime
from forex_python.converter import CurrencyRates
from num2words import num2words

# DB Setup
conn = sqlite3.connect('finance_goals.db', check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, amount REAL, currency TEXT, years REAL)")
c.execute("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, goal_id INTEGER, date TEXT, usd_sent REAL, inr_equiv REAL)")
conn.commit()

# Exchange Rate
c_rates = CurrencyRates()
try:
    exchange_rate = c_rates.get_rate('USD', 'INR')
except:
    exchange_rate = 83.0

# Sidebar - Select or Create Goal
st.sidebar.header("🎯 Your Financial Goals")
c.execute("SELECT id, title FROM goals")
goals = c.fetchall()
goal_titles = [f"{g[1]} (ID: {g[0]})" for g in goals]
goal_ids = [g[0] for g in goals]

selected_goal_index = st.sidebar.selectbox("Select a Goal", list(range(len(goal_titles))), format_func=lambda i: goal_titles[i]) if goals else None
selected_goal_id = goal_ids[selected_goal_index] if selected_goal_index is not None else None

st.sidebar.markdown("---")
st.sidebar.subheader("➕ Create New Goal")
with st.sidebar.form("new_goal_form"):
    new_title = st.text_input("Title (e.g., Loan, Buy a Bike)")
    new_amount = st.number_input("Target Amount", min_value=0.0, step=1000.0)
    new_currency = st.radio("Currency", ["INR", "USD"])
    new_years = st.number_input("Planned Duration (years)", min_value=0.1, step=0.1)
    create_goal = st.form_submit_button("Create Goal")

if create_goal and new_title:
    final_amount = new_amount * exchange_rate if new_currency == "USD" else new_amount
    c.execute("INSERT INTO goals (title, amount, currency, years) VALUES (?, ?, ?, ?)", (new_title, final_amount, "INR", new_years))
    conn.commit()
    st.success("🎯 New goal created! Refresh the page.")

# Main App - Show Selected Goal
if selected_goal_id:
    c.execute("SELECT title, amount FROM goals WHERE id = ?", (selected_goal_id,))
    goal = c.fetchone()
    title, amount_inr = goal

    st.title(f"📌 {title} Tracker")
    st.caption(f"Target: ₹{amount_inr:,.0f} ({num2words(round(amount_inr), lang='en_IN').title()} Rupees)")

    # Log Payments
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

    # Progress Section
    st.subheader("📊 Progress")
    c.execute("SELECT inr_equiv FROM payments WHERE goal_id = ?", (selected_goal_id,))
    total_paid = sum([p[0] for p in c.fetchall()])
    remaining = amount_inr - total_paid
    percent = total_paid / amount_inr * 100 if amount_inr > 0 else 0

    st.progress(min(percent / 100, 1.0))
    st.write(f"**Paid:** ₹{total_paid:,.0f} / ₹{amount_inr:,.0f} ({percent:.2f}%)")
    st.write(f"**Remaining:** ₹{remaining:,.0f}")

    # Custom Targets Section (in INR)
    st.subheader("📅 Custom Earning Targets in INR")
    use_custom_target = st.checkbox("✏️ Set your own earning target in INR")
    if use_custom_target:
        option = st.selectbox("Enter one of the following:", ["Daily", "Weekly", "Monthly", "Yearly"])
        inr_value = st.number_input(f"Enter your {option} INR earning goal", min_value=0.0)

        if option == "Daily":
            daily_inr = inr_value
        elif option == "Weekly":
            daily_inr = inr_value / 7
        elif option == "Monthly":
            daily_inr = inr_value / 30
        else:
            daily_inr = inr_value / 365

        # Derived values
        weekly_inr = daily_inr * 7
        monthly_inr = daily_inr * 30
        yearly_inr = daily_inr * 365

        # Convert to USD
        daily_usd = daily_inr / exchange_rate
        weekly_usd = weekly_inr / exchange_rate
        monthly_usd = monthly_inr / exchange_rate
        yearly_usd = yearly_inr / exchange_rate

        # Duration Estimate
        total_days = amount_inr / daily_inr if daily_inr > 0 else 0
        total_weeks = total_days / 7
        total_months = total_days / 30
        total_years = total_days / 365

        st.info(f"⏳ To reach ₹{amount_inr:,.0f}, you’ll need:")
        st.markdown(f"""
        - 🗓️ **{total_days:.0f} days**
        - 📆 **{total_weeks:.1f} weeks**
        - 📅 **{total_months:.1f} months**
        - 🕒 **{total_years:.2f} years**
        """)

        st.metric("Daily", f"₹{daily_inr:,.0f} → ${daily_usd:,.2f}")
        st.metric("Weekly", f"₹{weekly_inr:,.0f} → ${weekly_usd:,.2f}")
        st.metric("Monthly", f"₹{monthly_inr:,.0f} → ${monthly_usd:,.2f}")
        st.metric("Yearly", f"₹{yearly_inr:,.0f} → ${yearly_usd:,.2f}")

else:
    st.warning("No goal selected. Please create one from the sidebar.")
