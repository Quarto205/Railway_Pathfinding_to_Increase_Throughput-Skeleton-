import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Data Files
NETWORK_PATH = os.path.join(DATA_DIR, "railway_network_master.csv")
ROUTES_JSON_PATH = os.path.join(DATA_DIR, "train_specific_routes.json")
EDGES_CSV_PATH = os.path.join(DATA_DIR, "station_to_station_edges.csv") # Added assuming completeness
MODEL_PATH = os.path.join(MODELS_DIR, "train_precedence_agent.zip")

# Simulation Settings
DEFAULT_MAX_TRAVEL_TIME = 1.0

# Notification Service Settings
LLM_MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-r1:8b")
OLLAMA_API_URL = "http://localhost:11434/api/generate"
