import streamlit as st
import openai
import smtplib
from email.mime.text import MIMEText
import pandas as pd
import os

# Load secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]
EMAIL_USER = st.secrets["EMAIL_USER"]
EMAIL_PASS = st.secrets["EMAIL_PASS"]
EMAIL_TO   = st.secrets["EMAIL_TO"]

st.set_page_config(page_title="TCM Shop Assistant", layout="wide")

# --- HEADER ---
st.title("🌿 TCM Shop Assistant")
st.write("Welcome! You can ask about our products, book a consultation, or submit a query below.")

# --- CHATBOT INTERFACE ---
st.subheader("💬 Chat with the Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_input := st.chat_input("Ask me something..."):
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Call OpenAI (or your multi-agent logic here)
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    )
    reply = response.choices[0].message.content

    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)

# --- CLIENT FORM ---
st.subheader("📝 Leave Your Details")

with st.form("client_form"):
    name = st.text_input("Name")
    email = st.text_input("Email")
    query_type = st.selectbox("Query Type", ["Consultation", "Product Info", "Business Hours", "Other"])
    message = st.text_area("Your Message")

    submitted = st.form_submit_button("Submit")

    if submitted:
        if not name or not email or not message:
            st.error("⚠️ Please fill in all required fields.")
        else:
            # Save to CSV
            df = pd.DataFrame([{
                "Name": name,
                "Email": email,
                "Query Type": query_type,
                "Message": message
            }])
            file_exists = os.path.isfile("clients.csv")
            df.to_csv("clients.csv", mode="a", index=False, header=not file_exists)

            # Send Email
            try:
                msg = MIMEText(f"""
                New Client Query:
                Name: {name}
                Email: {email}
                Query Type: {query_type}
                Message: {message}
                """)
                msg["Subject"] = f"New Client Query - {query_type}"
                msg["From"] = EMAIL_USER
                msg["To"] = EMAIL_TO

                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(EMAIL_USER, EMAIL_PASS)
                    server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())

                st.success("✅ Your details have been submitted. We'll get back to you soon!")
            except Exception as e:
                st.error(f"❌ Email failed to send: {e}")
