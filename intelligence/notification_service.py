import requests
import os
import sys

# Perform absolute import for config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

class NotificationService:
    """
    Handles all communication with the local LLM to generate human-readable
    notifications from structured AI decisions.
    """
    def __init__(self):
        self.model_name = config.LLM_MODEL_NAME
        self.ollama_api_url = config.OLLAMA_API_URL
        print(f"INFO: Notification service initialized to use model '{self.model_name}'.")

    def generate(self, user_prompt):
        """
        Sends a system prompt and a user prompt to the local Ollama model.
        """
        system_prompt = (
            "You are an AI system for Indian Railways. Your only function is to generate "
            "a single-line, professional, operational command for a Station Master. "
            "Do not include explanations, headings, preambles, or any conversational text. "
            "Your output must be one single line of plain text or not more than two lines if necessary."
        )
        
        data = {
            "model": self.model_name,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False
        }
        
        print(f"\nINFO: Sending prompt to Ollama model '{data['model']}'...")
        try:
            response = requests.post(self.ollama_api_url, json=data)
            response.raise_for_status()
            print("INFO: Received response from Ollama.")
            return response.json()['response'].strip()
        except requests.exceptions.RequestException:
            print(f"\nFATAL ERROR: Could not connect to the Ollama server at {self.ollama_api_url}.")
            print("Please ensure Ollama is running and the model is downloaded.")
            return "[LLM OFFLINE] Notification generation failed."