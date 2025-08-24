import os
import openai
import asyncio
import pandas as pd
import streamlit as st
import re
import json
from datetime import datetime
from typing import Dict, Any, List, Callable

# ============================================================================
# MOCK AGENT FRAMEWORK CLASSES (These are placeholders for a real framework)
# ============================================================================

class RunContextWrapper:
    def __init__(self, conversation_history, messages):
        self.conversation_history = conversation_history
        self.messages = messages

class Agent:
    def __init__(self, name, instructions, tools=None, handoffs=None, model="gpt-4o-mini"):
        self.name = name
        self.instructions = instructions
        self.tools = tools if tools is not None else []
        self.handoffs = handoffs if handoffs is not None else []
        self.model = model

def function_tool(func: Callable):
    """A decorator to add a tool schema to a function for use with an LLM."""
    # This is a simplified mock of how a tool schema is created.
    # In a real framework, this would be more complex.
    schema = {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": func.__doc__,
            "parameters": {
                "type": "object",
                "properties": {
                    name: {"type": "string"} for name in func.__annotations__
                },
                "required": list(func.__annotations__.keys())
            }
        }
    }
    func.tool_schema = schema
    return func

def handoff(agent, on_handoff: Callable):
    return (agent, on_handoff)

async def Run(agent: Agent, conversation_history: str):
    """
    This is a corrected mock Run function that simulates the agent's behavior.
    It has been updated to be more robust for demonstration purposes.
    """
    log_system_message(f"MOCK-LLM: Simulating agent '{agent.name}'")
    
    input_lower = conversation_history.lower()
    
    # Check for specific product names or a broad product-related query
    product_keywords = ["product", "recommend", "remedy", "what do you have for"]
    product_names = [p["Product Name"].lower() for p in TCM_PRODUCTS]

    if any(keyword in input_lower for keyword in product_keywords) or any(name in input_lower for name in product_names):
        return type('obj', (object,), {'final_output': "ProductAgent"})
    
    # Check for consultation-related keywords
    elif "consultation" in input_lower or "book" in input_lower or "schedule" in input_lower or "appointment" in input_lower:
        return type('obj', (object,), {'final_output': "ConsultationAgent"})
        
    # Check for general keywords
    elif "hours" in input_lower or "location" in input_lower or "shipping" in input_lower or "business" in input_lower or "contact" in input_lower:
        return type('obj', (object,), {'final_output': "GeneralAgent"})
        
    # Default to Fallback
    else:
        return type('obj', (object,), {'final_output': "FallbackAgent"})


# ============================================================================
# CONFIGURATION AND SETUP
# ============================================================================

# Load environment variables (we will hardcode our data here instead)
# In a real app, this would be OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# We'll use a placeholder for this demonstration version.
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY_HERE"

if not OPENAI_API_KEY:
    st.error("OpenAI API Key not configured. Please add it to your environment.")
    st.stop()
    
# Hardcoded TCM Product Database
TCM_PRODUCTS = [
    {"Product Name": "12 Herb Bath Soak for Removing Dampness", "Used For": "Dampness, cold, joint pain, poor circulation, menstrual discomfort", "Description": "A herbal bath soak to expel dampness and cold from the body, improving circulation and relieving pain."},
    {"Product Name": "Harmony Mood Herbal Tea for Liver", "Used For": "Emotional balance, mood fluctuations, restlessness, healthy circulation, skin radiance", "Description": "A herbal tea blend designed to soothe the liver, promote emotional balance, and improve circulation for healthy, radiant skin."},
    {"Product Name": "Navel Patch for Dampness Cold Regulate Chi and Blood Digestion System Sleep Lose Weight", "Used For": "Dampness, cold, uterine cold, cold hands and feet, digestive health, bloating, indigestion, pain relief, insomnia, weight loss, immune enhancement", "Description": "A navel patch that combines moxibustion heat and warming herbs to eliminate dampness and cold, improve digestion, regulate qi and blood, and aid in weight management and sleep."},
    {"Product Name": "Ginger & Wormwood Herbal Foot Soak", "Used For": "Cold hands and feet, poor blood circulation, muscle aches, insomnia", "Description": "An herbal foot soak that warms the meridians, promotes blood circulation, and soothes the mind for better sleep."},
    {"Product Name": "Dang Gui & Goji Berry Herbal Soup Pack", "Used For": "Blood deficiency, fatigue, pale complexion, general weakness", "Description": "A nourishing herbal soup pack to tonify blood, boost energy, and improve overall vitality."},
    {"Product Name": "Herbal Face Steam for Radiance", "Used For": "Dull skin, skin radiance concerns, facial tension, stress relief", "Description": "A blend of liver-soothing herbs for a face steam to promote a healthy complexion and relieve stress-induced muscle tension."},
    {"Product Name": "Herbal Compress for Joint Pain", "Used For": "Joint pain, muscle aches, wind-dampness, rheumatoid stiffness", "Description": "A warm herbal compress to expel wind and dampness, relax tendons, and promote circulation to alleviate joint and muscle pain."},
]

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def log_system_message(message):
    """Add a timestamped message to system logs."""
    if 'system_logs' not in st.session_state:
        st.session_state['system_logs'] = []
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state['system_logs'].append(f"[{timestamp}] {message}")

@function_tool
def get_product_info(symptoms: str) -> str:
    """
    Searches for TCM products based on a list of symptoms.
    This tool is used by the ProductAgent.
    """
    log_system_message(f"TOOL: Searching products for symptoms: {symptoms}")
    matching_products = []
    
    # Split the input string into a list of keywords
    search_keywords = [keyword.strip().lower() for keyword in symptoms.replace(' and ', ',').split(',')]
    
    # Check for specific product names in the query to handle "tell me about"
    product_names = [p["Product Name"].lower() for p in TCM_PRODUCTS]
    for name in product_names:
        if name in symptoms.lower():
            # If a product name is found, search for it specifically.
            for p in TCM_PRODUCTS:
                if p["Product Name"].lower() == name:
                    return f"Found the following product:\n- **{p['Product Name']}**: {p['Description']} (Used for: {p['Used For']})\n"
    
    # If no specific product name is found, fall back to searching by symptoms.
    for product in TCM_PRODUCTS:
        product_used_for = product["Used For"].lower()
        # Check if any of the keywords are present in the 'Used For' string
        if any(keyword in product_used_for for keyword in search_keywords):
            matching_products.append(product)
            
    if not matching_products:
        return "No products found for the specified symptoms."
    
    # Format the output nicely for the agent
    formatted_output = "Found the following products:\n"
    for p in matching_products:
        formatted_output += f"- **{p['Product Name']}**: {p['Description']} (Used for: {p['Used For']})\n"
    
    return formatted_output

@function_tool
def redirect_to_booking_page(url: str) -> str:
    """Provides a formatted link for users to book a consultation.
    This tool is used by the ConsultationAgent.
    """
    log_system_message(f"TOOL: Providing booking link: {url}")
    return f"You can book your consultation here: {url}"

# ============================================================================
# AGENT CREATION
# ============================================================================

def create_agent_system():
    """Create and configure all agents for the TCM shop."""
    
    # Define the model to use.
    MODEL_NAME = "gpt-4o-mini"
    
    # The Product Agent uses our hardcoded product data via a Python tool.
    product_agent = Agent(
        name="ProductAgent",
        instructions="""
        You are a traditional Chinese medicine (TCM) product expert.
        Your task is to recommend products from a provided list based on the user's symptoms.
        
        When a user describes their symptoms, use the `get_product_info` tool with the user's
        symptoms as the input. Do not make up product names or descriptions.
        If no products match, politely inform the user.
        """,
        tools=[function_tool(get_product_info)],
        model=MODEL_NAME
    )
    
    # The Consultation Agent redirects the user to a booking page.
    consultation_agent = Agent(
        name="ConsultationAgent",
        instructions="""
        You are a consultation booking assistant for a TCM clinic.
        Your task is to help the user book a consultation.
        
        When a user asks to book a consultation, use the `redirect_to_booking_page` tool with the URL
        'https://www.betterfortoday.com/book-a-consultation' to provide them with a direct link.
        """,
        tools=[function_tool(redirect_to_booking_page)],
        model=MODEL_NAME
    )
    
    # The General Agent handles all other queries and FAQs.
    general_agent = Agent(
        name="GeneralAgent",
        instructions="""
        You are a customer service representative for a TCM shop.
        Your task is to answer general questions about the shop, such as business hours, location, or shipping.
        
        Use the following information to answer user questions:
        - Business Hours: Monday to Friday, 9:00 AM - 6:00 PM. We are closed on weekends and public holidays.
        - Location: 123 Herb Street, Singapore, 123456.
        - Shipping: We offer free local shipping for orders above $50. International shipping is also available.
        - Contact: You can reach us at contact@tcmshop.com or call us at +65 1234 5678.
        
        If a user asks about a product, hand off to the ProductAgent.
        If a user asks about booking, hand off to the ConsultationAgent.
        """,
        tools=[], # No special tools needed, just information retrieval from prompt
        model=MODEL_NAME
    )

    # The Fallback Agent for unclassified queries.
    fallback_agent = Agent(
        name="FallbackAgent",
        instructions="""
        You are a fallback assistant for a TCM shop.
        Your task is to provide a polite and helpful response when the user's query cannot be classified by the main agents.
        
        Acknowledge the user's message and explain that you could not understand their request.
        Suggest that they rephrase their query or contact a human for more complex issues.
        The human contact email is support@tcmshop.com.
        """,
        tools=[],
        model=MODEL_NAME
    )
    
    # The main router agent orchestrates all other agents.
    # Its prompt must be carefully designed to categorize user requests accurately.
    main_router_agent = Agent(
        name="MainRouter",
        instructions=f"""
        You are the main router for a TCM shop multi-agent system.
        Your role is to analyze a user's initial message and route it to the appropriate specialized agent.
        
        The available agents are:
        - ProductAgent: Use this for queries related to symptoms, product recommendations, or product information.
        - ConsultationAgent: Use this for requests to book an appointment or consultation.
        - GeneralAgent: Use this for all other inquiries, such as business hours, location, shipping, or contact information.
        - FallbackAgent: Use this if the query cannot be confidently classified.
        
        Your output must be the name of one of the agents listed above. Do not respond with anything else.
        Example output: "ProductAgent"
        """,
        handoffs=[
            handoff(product_agent, on_handoff=lambda ctx: log_system_message("HANDOFF: Routing to ProductAgent")),
            handoff(consultation_agent, on_handoff=lambda ctx: log_system_message("HANDOFF: Routing to ConsultationAgent")),
            handoff(general_agent, on_handoff=lambda ctx: log_system_message("HANDOFF: Routing to GeneralAgent")),
            handoff(fallback_agent, on_handoff=lambda ctx: log_system_message("HANDOFF: Routing to FallbackAgent"))
        ],
        model=MODEL_NAME
    )
    
    return main_router_agent

# ============================================================================
# MESSAGE PROCESSING
# ============================================================================

async def process_user_message(user_input):
    """Process user message through the agent system."""
    if 'conversation_history' not in st.session_state:
        st.session_state['conversation_history'] = ""
    
    if st.session_state['conversation_history']:
        st.session_state['conversation_history'] += f"\nUser: {user_input}"
    else:
        st.session_state['conversation_history'] = user_input
    
    log_system_message(f"PROCESSING: New message: {user_input[:50]}...")
    
    try:
        if 'main_router_agent' not in st.session_state:
            log_system_message("PROCESSING: Creating main router agent")
            st.session_state['main_router_agent'] = create_agent_system()
        
        log_system_message("PROCESSING: Running through main router")
        
        # This part simulates the agent's routing and response.
        # In a real-world scenario, the runner would execute the full workflow.
        router_result = await Run(st.session_state['main_router_agent'], user_input)
        agent_name = router_result.final_output.strip()
        
        if agent_name == "ProductAgent":
            agent_response = get_product_info(user_input)
        elif agent_name == "ConsultationAgent":
            agent_response = redirect_to_booking_page("https://www.betterfortoday.com/book-a-consultation")
        elif agent_name == "GeneralAgent":
            agent_response = "I can answer general questions, such as business hours or location."
        else:
            agent_response = "I'm sorry, I didn't understand your request. Please rephrase it."

        log_system_message(f"PROCESSING: Routed to: {agent_name}")
        log_system_message(f"PROCESSING: Generated response: {agent_response[:50]}...")

        st.session_state['conversation_history'] += f"\nAssistant: {agent_response}"
        st.session_state['messages'].append({"role": "user", "content": user_input})
        st.session_state['messages'].append({"role": "assistant", "content": agent_response})
        
        return agent_response
        
    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        log_system_message(f"PROCESSING ERROR: {error_msg}")
        return "I apologize, but there was an error processing your message. Please try again."

# ============================================================================
# STREAMLIT UI
# ============================================================================

def render_sidebar():
    """Render the sidebar with configuration and controls."""
    st.sidebar.title("System Configuration")
    
    # API Key status
    if OPENAI_API_KEY:
        st.sidebar.success("✅ OpenAI API Key configured")
    else:
        st.sidebar.error("❌ OpenAI API Key not configured")

    # Control buttons
    if st.sidebar.button("🔄 Reset Conversation"):
        st.session_state['messages'] = []
        st.session_state['conversation_history'] = ""
        log_system_message("SYSTEM: Conversation reset")
        st.rerun()
    
    # Display product list
    st.sidebar.subheader("TCM Product List (Knowledge Base)")
    st.sidebar.markdown("This is the data the 'ProductAgent' uses to make recommendations.")
    
    product_df = pd.DataFrame(TCM_PRODUCTS)
    st.sidebar.dataframe(product_df, use_container_width=True)
    
    # System logs
    st.sidebar.subheader("System Logs")
    log_container = st.sidebar.container(height=300)
    with log_container:
        for log in st.session_state['system_logs']:
            st.text(log)

def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="TCM Shop Assistant",
        page_icon="🌿",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🌿 TCM Shop Assistant")
    st.markdown("Welcome! I'm here to help you feel better today. You can ask me about our products, book a consultation, or ask general questions about the shop.")
    
    if 'messages' not in st.session_state:
        st.session_state['messages'] = []
    if 'system_logs' not in st.session_state:
        st.session_state['system_logs'] = []
    if 'main_router_agent' not in st.session_state:
        st.session_state['main_router_agent'] = create_agent_system()
        
    render_sidebar()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        for message in st.session_state['messages']:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        user_input = st.chat_input("What can I help you with?")
        if user_input:
            asyncio.run(process_user_message(user_input))
            st.rerun()
    
    with col2:
        st.subheader("Example Queries")
        st.markdown("""
        * "I have cold hands and feet, what do you recommend?"
        * "How can I book a consultation?"
        * "What are your business hours?"
        * "Can you tell me about the Harmony Mood Herbal Tea?"
        * "Do you sell any products for insomnia?"
        * "I'm looking for a product to help with digestion and cold hands."
        """)

if __name__ == "__main__":
    main()
