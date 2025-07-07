import streamlit as st
import sqlite3
from datetime import datetime
from forex_python.converter import CurrencyRates
from num2words import num2words

# Get live USD to INR rate
c_rates = CurrencyRates()
try:
    exchange_rate = c_rates.get_rate('USD', 'INR')
except:
    exchange_rate = 83.0  # fallback

# Connect to DB
conn = sqlite3.connect('loan_data.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    usd_sent REAL,
    inr_equiv REAL
)''')

# App title
st.title("💸 Loan Payoff Calculator & USD Tracker")

# Step 1: Loan Input
st.header("1️⃣ Enter Your Loan Details")
loan_amount = st.number_input("Enter your total loan amount", min_value=0.0, step=1000.0, format="%.2f")
loan_currency = st.radio("Is this amount in:", ["INR", "USD"])
if loan_currency == "USD":
    total_loan_inr = loan_amount * exchange_rate
    st.write(f"Converted to INR: ₹{total_loan_inr:,.0f}")
else:
    total_loan_inr = loan_amount
    st.write(f"Loan in INR: ₹{total_loan_inr:,.0f}")

loan_words = num2words(round(total_loan_inr), lang='en_IN').title()
st.success(f"({loan_words} Rupees)")

# Step 2: Target Period
st.header("2️⃣ In How Many Years Will You Pay?")
repay_years = st.number_input("Enter number of years", min_value=1, step=1)

weeks = repay_years * 52
months = repay_years * 12
days = repay_years * 365

# Weekly, Monthly, Daily amount to send
weekly_inr_needed = total_loan_inr / weeks
monthly_inr_needed = total_loan_inr / months
daily_inr_needed = total_loan_inr / days

# Convert to USD
weekly_usd_needed = weekly_inr_needed / exchange_rate
monthly_usd_needed = monthly_inr_needed / exchange_rate
daily_usd_needed = daily_inr_needed / exchange_rate
yearly_usd_needed = (total_loan_inr / exchange_rate) / repay_years

# Show Targets
st.header("📊 How Much You Need to Send & Earn")
st.metric("Per Week: Send", f"₹{weekly_inr_needed:,.0f} → ${weekly_usd_needed:,.2f}")
st.metric("Per Month: Send", f"₹{monthly_inr_needed:,.0f} → ${monthly_usd_needed:,.2f}")
st.metric("Per Day: Earn", f"₹{daily_inr_needed:,.0f} → ${daily_usd_needed:,.2f}")
st.metric("Per Year: Send", f"${yearly_usd_needed:,.2f}")

# Step 3: Payment Logging
st.header("3️⃣ Log Your Weekly USD Payment")
with st.form("payment_form"):
    usd_sent = st.number_input("USD Sent This Week", min_value=0.0, step=1.0)
    pay_date = st.date_input("Date", value=datetime.today())
    submitted = st.form_submit_button("Log Payment")
    if submitted:
        inr_equiv = usd_sent * exchange_rate
        c.execute("INSERT INTO payments (date, usd_sent, inr_equiv) VALUES (?, ?, ?)",
                  (pay_date.strftime("%Y-%m-%d"), usd_sent, inr_equiv))
        conn.commit()
        st.success("✅ Payment logged successfully!")

# Step 4: Show Progress
st.header("4️⃣ Payment Progress")
payments = c.execute("SELECT usd_sent, inr_equiv FROM payments").fetchall()
paid_inr = sum([p[1] for p in payments])
remaining_inr = total_loan_inr - paid_inr
percent = (paid_inr / total_loan_inr) * 100 if total_loan_inr > 0 else 0

st.progress(min(percent / 100, 1.0))
st.write(f"**Total Paid:** ₹{paid_inr:,.0f}")
st.write(f"**Remaining:** ₹{remaining_inr:,.0f}")
st.write(f"**Completed:** {percent:.2f}%")

# Step 5: Show History
st.header("📒 Payment History")
if payments:
    st.table([{"USD Sent": p[0], "INR Value": p[1]} for p in payments])
else:
    st.info("No payments logged yet.")
