class PrecedenceAgent:
    """
    Sanitized Tactical Agent: Replaces RL model with simple priority rules.
    """
    def __init__(self, model_path=None):
        print("INFO: Loading basic rules-based precedence agent (ML model disabled).")

    def decide(self, conflict_data):
        """
        Uses simple heuristic to decide which train gets precedence,
        standing in for the proprietary RL model.
        """
        t1 = conflict_data['train1']
        t2 = conflict_data['train2']
        if t1.get('priority', 0) >= t2.get('priority', 0):
            return t1
        return t2
    
