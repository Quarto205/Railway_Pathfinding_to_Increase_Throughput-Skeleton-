import os
import json
from datetime import datetime
import config

# Import all the new modules
from core.pathfinder import RailwayPathfinder, Train
from intelligence.precedence_agent import PrecedenceAgent
from intelligence.strategic_planner import StrategicPlanner
from intelligence.notification_service import NotificationService

class Simulation:
    """The main orchestrator for the entire simulation."""
    def __init__(self):
        # Define paths from config
        print("--- AI Train Controller Initializing ---")
        self.pathfinder = RailwayPathfinder(config.NETWORK_PATH)
        self.precedence_agent = PrecedenceAgent(config.MODEL_PATH)
        self.strategic_planner = StrategicPlanner()
        self.notifier = NotificationService()
        
        # Load all train routes into memory 
        try:
            with open(config.ROUTES_JSON_PATH, 'r', encoding='utf-8') as f:
                self.all_trains_data = json.load(f)
        except FileNotFoundError:
            print(f"FATAL ERROR: The routes file '{config.ROUTES_JSON_PATH}' was not found.")
            exit()
            
        self.blockages = []

    def _parse_time_string(self, time_str):
        """Helper to parse 'HH.MM' or 'HH:MM' into a datetime.time object."""
        if not isinstance(time_str, str) or time_str.strip() in ['-', '']:
            return None
        try:
            time_str = time_str.replace('.', ':')
            return datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            return None

    def _time_to_minutes_of_week(self, day, time_obj):
        """Converts a day of the week and a time object to total minutes from the start of the week."""
        if time_obj is None or day is None:
            return None
        # Day 1 (Mon) @ 00:00 is 0 minutes. Day 7 (Sun) @ 23:59 is the max.
        return (int(day) - 1) * 1440 + time_obj.hour * 60 + time_obj.minute
    
    def _find_next_affected_train(self, station1, station2):
        """
        Finds the next train scheduled to pass through the blocked segment
        based on the current system time.
        """
        now = datetime.now()
        current_day = now.weekday() + 1  # Monday is 1, ..., Sunday is 7
        current_time = now.time()
        current_abs_minutes = self._time_to_minutes_of_week(current_day, current_time)
        
        print(f"\nINFO: Current time is Day {current_day}, {current_time.strftime('%H:%M')}. Searching for next scheduled train on {station1}-{station2} segment.")

        candidate_trains = []

        for train_key, train_details in self.all_trains_data.items():
            route_details = train_details.get('route_details', [])
            station_codes = [s.get('Code') for s in route_details]

            try:
                idx1 = station_codes.index(station1)
                idx2 = station_codes.index(station2)
            except ValueError:
                continue

            if abs(idx1 - idx2) == 1:
                # This segment is in the train's route. Check the schedule.
                dep_station_details = route_details[min(idx1, idx2)]
                dep_time = self._parse_time_string(dep_station_details.get('Dep.'))
                dep_day = dep_station_details.get('Day')

                if dep_time and dep_day and dep_day in train_details.get('running_days',[]):
                    scheduled_dep_abs_minutes = self._time_to_minutes_of_week(dep_day, dep_time)

                    # Check if this departure is in the future relative to the current time
                    if scheduled_dep_abs_minutes >= current_abs_minutes:
                        time_diff = scheduled_dep_abs_minutes - current_abs_minutes
                        candidate_trains.append((time_diff, train_details))
        
        if candidate_trains:
            # Sort by the time difference to find the soonest train
            candidate_trains.sort(key=lambda x: x[0])
            return candidate_trains[0][1] # Return the train_data dictionary
        else:
            return None


    def _find_affected_trains_for_maintenance(self, station1, station2, day_of_week, start_time, end_time):
        """
        Scans all train schedules to find trains affected by a planned blockage.
        This version uses a robust absolute minute-of-the-week calculation to correctly
        handle overnight schedules.
        """
        print(f"\nINFO: Searching for trains affected by blockage {station1}-{station2} on day {day_of_week} between {start_time.strftime('%H:%M')} and {end_time.strftime('%H:%M')}...")
        affected_trains = []

        # --- Convert maintenance window to absolute minutes ---
        maintenance_start_day = day_of_week
        maintenance_end_day = day_of_week
        # Handle overnight maintenance window
        if end_time < start_time:
            maintenance_end_day += 1
            if maintenance_end_day > 7:
                 maintenance_end_day = 1
        
        m_start_abs = self._time_to_minutes_of_week(maintenance_start_day, start_time)
        m_end_abs = self._time_to_minutes_of_week(maintenance_end_day, end_time)

        for train_name_key, train_details in self.all_trains_data.items():
            route_details = train_details.get('route_details', [])
            station_codes = [s.get('Code') for s in route_details]

            try:
                idx1 = station_codes.index(station1)
                idx2 = station_codes.index(station2)
            except ValueError:
                continue

            if abs(idx1 - idx2) == 1:
                first_station_details = route_details[min(idx1, idx2)]
                second_station_details = route_details[max(idx1, idx2)]
                
                dep_time = self._parse_time_string(first_station_details.get('Dep.'))
                arr_time = self._parse_time_string(second_station_details.get('Arr.'))
                dep_day = first_station_details.get('Day')
                arr_day = second_station_details.get('Day')

                if all([dep_time, arr_time, dep_day, arr_day]):
                    t_start_abs = self._time_to_minutes_of_week(dep_day, dep_time)
                    t_end_abs = self._time_to_minutes_of_week(arr_day, arr_time)
                    
                    if max(m_start_abs, t_start_abs) < min(m_end_abs, t_end_abs):
                        affected_trains.append(train_details)
                        print(f"  -> Found match: {train_details['train_number']} {train_details['train_name']} (Scheduled on segment at Day {dep_day}, {dep_time.strftime('%H:%M')})")
        
        if not affected_trains:
            print("INFO: No trains found matching the specified maintenance schedule.")
        return affected_trains

    def run_maintenance_simulation(self):
        """Handles the user interaction and workflow for maintenance planning."""
        print("\n--- Maintenance Planning Mode ---")
        print("This tool will identify all trains affected by a scheduled track blockage and generate an operational plan.")
        
        station1 = input("Enter the FIRST station code for the blockage (e.g., CNB): ").upper().strip()
        station2 = input("Enter the SECOND station code for the blockage (e.g., ON): ").upper().strip()
        
        day_map = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7}
        day_input = input("Enter the day of the week (Mon, Tue, Wed, Thu, Fri, Sat, Sun): ").lower().strip()[:3]
        day_of_week = day_map.get(day_input)
        if day_of_week is None:
            print("Invalid day of the week. Exiting.")
            return
            
        try:
            start_time_str = input("Enter maintenance start time (24h format, HH:MM): ")
            end_time_str = input("Enter maintenance end time (24h format, HH:MM): ")
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
            end_time = datetime.strptime(end_time_str, "%H:%M").time()
        except ValueError:
            print("Invalid time format. Please use HH:MM. Exiting.")
            return

        affected_trains = self._find_affected_trains_for_maintenance(station1, station2, day_of_week, start_time, end_time)

        if not affected_trains:
            return

        consolidated_plan = self.strategic_planner.plan_for_maintenance(affected_trains, station1, station2, self.pathfinder)
        
        print("\n\n" + "="*30)
        print("  MAINTENANCE OPERATIONAL PLAN")
        print("="*30)
        print(f"Blockage: {station1} <-> {station2}")
        print(f"Schedule: Day {day_of_week} from {start_time_str} to {end_time_str}")
        print("-"*30)

        for plan_item in consolidated_plan:
            train_info = plan_item['train_info']
            decision = plan_item['decision']
            result = plan_item['result']
            reroute_point = plan_item['reroute_point']
            
            print(f"\nTrain: {train_info['train_number']} {train_info['train_name']}")
            print(f"Decision: {decision}")

            if decision == "REROUTE":
                prompt = f"Data:\\n- Event: Rerouting\\n- Train: {train_info['train_number']} ({train_info['train_name']})\\n- From Station: {reroute_point}\\n- New Path: {' -> '.join(result['path'])}\\n- Reason: To avoid scheduled maintenance block.\\nFinal Instruction:"
                print(f"Action: Reroute from {reroute_point} via {' -> '.join(result['path'])}")
            else: # HOLD
                prompt = f"Data:\\n- Event: Hold Order\\n- Train: {train_info['train_number']} ({train_info['train_name']})\\n- At Station: {reroute_point}\\n- Reason: {result}\\nFinal Instruction:"
                print(f"Action: Hold at station {reroute_point}.")

            notification = self.notifier.generate(prompt)
            print(f"Generated Command: {notification}")
            print("-"*30)


    def run_realtime_simulation(self):
        """Runs the original real-time blockage simulation with dynamic train selection."""
        print("\n--- Real-time Blockage Mode ---")
        blockage_input = input("Enter blockage (e.g., 'CNB-ON'): ")
        self.blockages = self.parse_blockage_input(blockage_input)
        if not self.blockages:
            print("Could not parse blockage input. Exiting.")
            return

        blocked_from, blocked_to = self.blockages[0]
        
        # NEW: Dynamically find the next train affected by this blockage
        train_info = self._find_next_affected_train(blocked_from, blocked_to)
        
        if not train_info:
            print(f"\nINFO: No trains are scheduled to run on the {blocked_from}-{blocked_to} segment in the near future.")
            return
            
        print(f"INFO: Simulating blockage for the next scheduled train: {train_info['train_number']} {train_info['train_name']}")
        
        # Determine the reroute point (the station just before the blockage)
        route_stations = [s['Code'] for s in train_info['route_details']]
        try:
            idx_from = route_stations.index(blocked_from)
            idx_to = route_stations.index(blocked_to)
            reroute_point = blocked_from if idx_from < idx_to else blocked_to
        except ValueError:
            # This should not happen if _find_next_affected_train works correctly
            print(f"ERROR: A logic error occurred. The blocked stations {blocked_from}-{blocked_to} are not a direct segment in the identified train's route.")
            return
            
        print(f"INFO: Blockage detected ahead. Rerouting decision point is {reroute_point}.")
        
        # Get train priority from its type
        priority_map = {"Superfast": 5, "Express": 3, "Passenger": 1}
        train_type = train_info.get("train_type", "Express")
        priority = priority_map.get(train_type, 3) # Default to Express
        affected_train = Train(priority=priority)
        
        destination = train_info.get("destination")

        # Call the strategic planner to get a high-level decision
        decision, result = self.strategic_planner.analyze_blockage(
            train=affected_train,
            source=reroute_point,
            destination=destination,
            blockages=self.blockages,
            pathfinder=self.pathfinder
        )
        
        print(f"     -> STRATEGIC DECISION: {decision}")
        
        # --- Generate Notification for the correct Station Master ---
        if decision == "REROUTE":
            prompt = f"Data:\\n- Event: Rerouting\\n- Train: {train_info['train_number']} ({train_info['train_name']})\\n- From Station: {reroute_point}\\n- New Path: {' -> '.join(result['path'])}\\n- Reason: To avoid network blockage.\\nFinal Instruction:"
        else: # HOLD
            prompt = f"Data:\\n- Event: Hold Order\\n- Train: {train_info['train_number']} ({train_info['train_name']})\\n- At Station: {reroute_point}\\n- Reason: {result}\\nFinal Instruction:"
        
        notification = self.notifier.generate(prompt)
        print("\n--- FINAL NOTIFICATION ---")
        print(notification)
        print("--------------------------")

    def parse_blockage_input(self, input_string):
        """Parses the user's input string for blockages (e.g., 'A-B' or 'A to B, C to D')."""
        blockages = []
        # Split by comma for multiple blockages
        parts = input_string.split(',')
        for part in parts:
            part = part.strip().upper()
            if ' TO ' in part:
                stations = part.split(' TO ')
            elif '-' in part:
                stations = part.split('-')
            else:
                continue
                
            if len(stations) == 2:
                blockages.append((stations[0].strip(), stations[1].strip()))
        return blockages

if __name__ == "__main__":
    simulation = Simulation()
    print("\nSelect Simulation Mode:")
    print("1: Real-time Blockage (Original Simulation)")
    print("2: Proactive Maintenance Planning (New Feature)")
    
    choice = input("Enter your choice (1 or 2): ")
    
    if choice == '1':
        simulation.run_realtime_simulation()
    elif choice == '2':
        simulation.run_maintenance_simulation()
    else:
        print("Invalid choice. Exiting.")

