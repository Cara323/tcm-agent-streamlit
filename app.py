import os
import openai
import asyncio
import pandas as pd
import streamlit as st
import re
from datetime import datetime
from typing import Dict, Any, List

# A placeholder for the actual `agents` module and its classes.
# In a real-world scenario, you would import these from a local file.
class RunContextWrapper:
    def __init__(self, conversation_history, messages):
        self.conversation_history = conversation_history
        self.messages = messages

class Agent:
    def __init__(self, name, instructions, tools=None, handoffs=None):
        self.name = name
        self.instructions = instructions
        self.tools = tools if tools is not None else []
        self.handoffs = handoffs if handoffs is not None else []

async def Run(agent, conversation_history):
    # This is a mock function to simulate the agent's response.
    # In a real implementation, this would involve a call to the LLM.
    response = ""
    # Simplified logic for demonstration purposes
    if "product" in agent.name.lower() and ("product" in conversation_history.lower() or "dampness" in conversation_history.lower() or "insomnia" in conversation_history.lower()):
        response = "ProductAgent"
    elif "consultation" in agent.name.lower() and "consultation" in conversation_history.lower():
        response = "ConsultationAgent"
    elif "general" in agent.name.lower() and ("hours" in conversation_history.lower() or "location" in conversation_history.lower() or "shipping" in conversation_history.lower()):
        response = "GeneralAgent"
    elif "fallback" in agent.name.lower():
        response = "FallbackAgent"
    
    # This part mocks the router agent's decision.
    if "product" in conversation_history.lower() or "dampness" in conversation_history.lower() or "insomnia" in conversation_history.lower():
        return type('obj', (object,), {'final_output': "ProductAgent"})
    elif "consultation" in conversation_history.lower() or "book" in conversation_history.lower():
        return type('obj', (object,), {'final_output': "ConsultationAgent"})
    elif "hours" in conversation_history.lower() or "location" in conversation_history.lower() or "shipping" in conversation_history.lower():
        return type('obj', (object,), {'final_output': "GeneralAgent"})
    else:
        return type('obj', (object,), {'final_output': "FallbackAgent"})


def function_tool(func):
    # A simple decorator to mark functions as tools for the agent.
    return func

def handoff(agent, on_handoff):
    return (agent, on_handoff)

# ============================================================================
# CONFIGURATION AND SETUP
# ============================================================================

# Load environment variables (we will hardcode our data here instead)
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_KEY = "sk-...0UwA" # Use a placeholder for the immersive

if not OPENAI_API_KEY:
    st.error("OpenAI API Key not configured. Please add it to your .env file or hardcode it.")
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

def get_product_info(symptoms: str) -> str:
    """
    Search for TCM products based on a list of symptoms.
    This function acts as our shared memory/database for the ProductAgent.
    """
    log_system_message(f"TOOL: Searching products for symptoms: {symptoms}")
    matching_products = []
    
    # Split the input string into a list of keywords
    search_keywords = [keyword.strip().lower() for keyword in symptoms.split(',')]
    
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

def redirect_to_booking_page(url: str) -> str:
    """Provides a formatted link for users to book a consultation."""
    log_system_message(f"TOOL: Providing booking link: {url}")
    return f"You can book your consultation here: {url}"

# ============================================================================
# AGENT CREATION
# ============================================================================

def create_agent_system():
    """Create and configure all agents for the TCM shop."""
    
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
        tools=[function_tool(get_product_info)]
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
        tools=[function_tool(redirect_to_booking_page)]
    )
    
    # The Gene
