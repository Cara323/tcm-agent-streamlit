# app.py
import os, asyncio, requests, pandas as pd, streamlit as st
from pathlib import Path
from datetime import datetime
from typing import Callable

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG (from secrets with sensible defaults)
# Add these in Streamlit Secrets; defaults used if missing so dev works locally
# ─────────────────────────────────────────────────────────────────────────────
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "")  # not used yet; reserved for future
SENDGRID_API_KEY = st.secrets.get("SENDGRID_API_KEY", "")
EMAIL_FROM = st.secrets.get("EMAIL_FROM", "")          # must be a verified sender in SendGrid
EMAIL_TO = st.secrets.get("EMAIL_TO", EMAIL_FROM or "")

# Branding (optional: set in secrets; otherwise defaults apply)
BRAND_NAME = st.secrets.get("BRAND_NAME", "Better For Today")
BRAND_TAG = st.secrets.get("BRAND_TAG", "TCM Shop")
BRAND_PRIMARY = st.secrets.get("BRAND_PRIMARY", "#0b6b3a")  # your primary brand color
LOGO_URL = st.secrets.get("LOGO_URL", "")                   # https image url (optional)
SITE_URL = st.secrets.get("SITE_URL", "https://www.betterfortoday.com")
ADDRESS = st.secrets.get("ADDRESS", "123 Herb Street, Singapore")
CONTACT_EMAIL = st.secrets.get("CONTACT_EMAIL", "contact@tcmshop.com")

# ─────────────────────────────────────────────────────────────────────────────
# STREAMLIT PAGE
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title=f"{BRAND_NAME} Assistant", page_icon="🌿", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# MOCK AGENT ROUTER (simple keyword router like your original)
# ─────────────────────────────────────────────────────────────────────────────
class Agent:
    def __init__(self, name, instructions, tools=None, model="gpt-4o-mini"):
        self.name = name; self.instructions = instructions
        self.tools = tools or []; self.model = model

async def Run(agent: Agent, text: str):
    t = text.lower()
    product_kw = ["product","recommend","remedy","what do you have for",
                  "tell me about","help with","dampness","insomnia",
                  "cold hands","fatigue","circulation","tea","soak",
                  "patch","soup","herbal"]
    names = [p["Product Name"].lower() for p in TCM_PRODUCTS]
    if any(k in t for k in product_kw) or any(n in t for n in names): return "ProductAgent"
    if any(k in t for k in ["consultation","book","schedule","appointment"]): return "ConsultationAgent"
    if any(k in t for k in ["hours","hour","location","address","shipping","deliver","business","contact","phone","email"]): return "GeneralAgent"
    return "FallbackAgent"

# ─────────────────────────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────────────────────────
TCM_PRODUCTS = [
    {"Product Name":"12 Herb Bath Soak for Removing Dampness","Used For":"Dampness, cold, joint pain, poor circulation, menstrual discomfort","Description":"A herbal bath soak to expel dampness and cold from the body, improving circulation and relieving pain."},
    {"Product Name":"Harmony Mood Herbal Tea for Liver","Used For":"Emotional balance, mood fluctuations, restlessness, healthy circulation, skin radiance","Description":"A herbal tea blend designed to soothe the liver, promote emotional balance, and improve circulation for healthy, radiant skin."},
    {"Product Name":"Navel Patch for Dampness Cold Regulate Chi and Blood Digestion System Sleep Lose Weight","Used For":"Dampness, cold, uterine cold, cold hands and feet, digestive health, bloating, indigestion, pain relief, insomnia, weight management, immune enhancement","Description":"A navel patch that combines moxibustion heat and warming herbs to eliminate dampness and cold, improve digestion, regulate qi and blood, and aid in weight management and sleep."},
    {"Product Name":"Ginger & Wormwood Herbal Foot Soak","Used For":"Cold hands and feet, poor blood circulation, muscle aches, insomnia","Description":"An herbal foot soak that warms the meridians, promotes blood circulation, and soothes the mind for better sleep."},
    {"Product Name":"Dang Gui & Goji Berry Herbal Soup Pack","Used For":"Blood deficiency, fatigue, pale complexion, general weakness","Description":"A nourishing herbal soup pack to tonify blood, boost energy, and improve overall vitality."},
    {"Product Name":"Herbal Face Steam for Radiance","Used For":"Dull skin, skin radiance concerns, facial tension, stress relief","Description":"A blend of liver-soothing herbs for a face steam to promote a healthy complexion and relieve stress-induced muscle tension."},
    {"Product Name":"Herbal Compress for Joint Pain","Used For":"Joint pain, muscle aches, wind-dampness, rheumatoid stiffness","Description":"A warm herbal compress to expel wind and dampness, relax tendons, and promote circulation to alleviate joint and muscle pain."},
]

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_product_info(q: str) -> str:
    lower = q.lower()

    # Exact product name match first
    for p in TCM_PRODUCTS:
        if p["Product Name"].lower() in lower:
            return (
                f"**{p['Product Name']}**\n\n"
                f"{p['Description']}\n\n"
                f"Used For: {p['Used For']}\n\n"
                "Let me know if you'd like to book a consultation or hear more!"
            )

    # Keyword matching fallback
    kws = [k.strip().lower() for k in q.replace(" and ", ",").split(",")]
    matching = [
        p for p in TCM_PRODUCTS
        if any(k and k in p["Used For"].lower() for k in kws)
    ]

    if matching:
        response = "Here are products that may help:\n\n"
        response += "\n".join(
            f"- **{p['Product Name']}**: {p['Description']} (Used for: {p['Used For']})"
            for p in matching
        )
        return response

    # Final fallback: show all
    return (
        "Sorry, there was no perfect match. Here's our full product list:\n\n" +
        "\n".join(
            f"- **{p['Product Name']}**: {p['Used For']}"
            for p in TCM_PRODUCTS
        )
    )


def booking_link() -> str:
    return f"Book your consultation here: {SITE_URL}/book-a-consultation"

def general_answer(q:str)->str:
    t=q.lower()
    h="Business Hours: Mon–Fri, 9am–6pm. Closed weekends/public holidays."
    l=f"Location: {ADDRESS}."
    s="Shipping: Free local shipping > $50. International available."
    c=f"Contact: {CONTACT_EMAIL} | +65 1234 5678."
    if "hour" in t: return h
    if "locat" in t or "address" in t: return l
    if "shipping" in t or "deliver" in t: return s
    if "contact" in t or "phone" in t or "email" in t: return c
    return "\n".join([h,l,s,c])

def send_via_sendgrid(name, email, query_type, message):
    """Owner (plain) + Client (HTML) via SendGrid; returns detailed status + shows error body."""
    import requests
    api_key = st.secrets["SENDGRID_API_KEY"].strip()
    from_email = st.secrets["EMAIL_FROM"].strip()
    to_owner = st.secrets["EMAIL_TO"].strip()

    owner_subject = f"[New Lead] {query_type} — {name}"
    owner_text = (
        "New client query received\n\n"
        f"Name: {name}\nEmail: {email}\nType: {query_type}\nMessage:\n{message}\n"
        f"\nTime: {datetime.now().isoformat(timespec='seconds')}"
    )

    client_subject = f"We received your query: {query_type}"
    client_text = (
        f"Hi {name or 'there'},\n\nThanks for reaching out! We received your message."
        f"\n\nType: {query_type}\nMessage: {message}\n\n— Better For Today"
    )
    client_html = f"""<!doctype html><html><body>
    <p>Hi {name or 'there'},</p><p>We received your message.</p>
    <p><b>Type:</b> {query_type}<br><b>Message:</b> {(message or '').strip()}</p>
    <p>— Better For Today</p></body></html>"""

    def _send(to_email, subject, text, html=None):
        payload = {
            "personalizations": [{"to": [{"email": to_email.strip()}]}],
            "from": {"email": from_email},
            "subject": subject,
            "content": [{"type": "text/plain", "value": text}],
        }
        if html:
            payload["content"].append({"type": "text/html", "value": html})

        r = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json=payload,
            timeout=10
        )
        try:
            body = r.json()
        except Exception:
            body = r.text
        return r.status_code, body

    o_code, o_body = _send(to_owner, owner_subject, owner_text)
    c_code, c_body = _send(email, client_subject, client_text, html=client_html)

    if o_code not in (200, 202):
        st.warning(f"Owner email error {o_code}: {str(o_body)[:400]}")
    if c_code not in (200, 202):
        st.warning(f"Client email error {c_code}: {str(c_body)[:400]}")

    return "ok" if o_code in (200, 202) and c_code in (200, 202) else f"owner:{o_code}, client:{c_code}"

# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────
st.title(f"🌿 {BRAND_NAME} Assistant")
st.markdown("Ask about products, consultations, or shop info. Leave your details below for a follow-up.")

left,right = st.columns([2,1], gap="large")

with left:
    st.session_state.setdefault("messages", [])
    for m in st.session_state["messages"]:
        with st.chat_message(m["role"]): st.write(m["content"])
    if q := st.chat_input("What can I help you with?"):
        agent = Agent("Router","Router")
        choice = asyncio.run(Run(agent,q))
        if choice=="ProductAgent": reply=get_product_info(q)
        elif choice=="ConsultationAgent": reply=booking_link()
        elif choice=="GeneralAgent": reply=general_answer(q)
        else: reply=f"Sorry, I didn’t understand. Please rephrase or email {CONTACT_EMAIL}."
        st.session_state["messages"] += [{"role":"user","content":q},{"role":"assistant","content":reply}]
        st.rerun()

with right:
    st.subheader("Example Queries")
    st.markdown("- I have cold hands and feet, what do you recommend?\n- How can I book a consultation?\n- What are your business hours?\n- Tell me about the Harmony Mood Herbal Tea.\n- Do you have anything for insomnia?\n- I need help with digestion and cold hands.")
    st.markdown("---")
    st.subheader("Leave your details")
    with st.form("client_form", clear_on_submit=True):
        c1,c2 = st.columns(2)
        with c1: name = st.text_input("Your Name")
        with c2: email = st.text_input("Your Email")
        query_type = st.selectbox("Query Type", ["Consultation","Product","Business Hours","Other"])
        message = st.text_area("Message", height=120)
        submitted = st.form_submit_button("Submit")

    if submitted:
        if not name or not email:
            st.error("Please provide name and email")
        else:
            # save CSV
            try:
                Path("data").mkdir(exist_ok=True, parents=True)
                fp = Path("data/client_queries.csv")
                row = {"timestamp":datetime.now().isoformat(timespec="seconds"),
                       "name":name.strip(),"email":email.strip(),
                       "query_type":query_type,"message":(message or "").strip()}
                if fp.exists():
                    df = pd.read_csv(fp)
                    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                else:
                    df = pd.DataFrame([row])
                df.to_csv(fp, index=False)
                st.caption(f"Saved to: `{fp}`")
            except Exception as e:
                st.warning(f"Could not save CSV: {e}")

            # send emails through SendGrid
            try:
                status = send_via_sendgrid(name, email, query_type, message or "")
                st.success("Submitted and emails sent!" if status=="ok" else f"Saved, but email status: {status}")
            except Exception as e:
                st.warning(f"Saved, but email failed: {e}")
