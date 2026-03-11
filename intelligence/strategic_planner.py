from core.pathfinder import Train

class StrategicPlanner:
    def analyze_blockage(self, train, source, destination, blockages, pathfinder):
        print(f"     -> Basic Planner: Reroute from {source} to {destination}...")
        paths = pathfinder.find_k_shortest_paths(source, destination, train, K=1, blockages=blockages)
        if paths:
            return "REROUTE", paths[0]
        return "HOLD", "No alternative path"

    def plan_for_maintenance(self, affected_trains, blockage_source, blockage_dest, pathfinder):
        print("--- BASIC BULK PLANNING ---")
        full_plan = []
        blockages = [(blockage_source, blockage_dest)]

        for train_info in affected_trains:
            train_name = train_info.get("train_name", "Unknown")
            print(f"Planning: {train_name}")
            route_stations = [s['Code'] for s in train_info.get('route_details', [])]
            try:
                idx1 = route_stations.index(blockage_source)
                idx2 = route_stations.index(blockage_dest)
                reroute_point = blockage_source if idx1 < idx2 else blockage_dest
            except ValueError:
                continue

            destination = train_info.get("destination")
            t_obj = Train(3) # fixed dummy priority
            
            decision, result = self.analyze_blockage(t_obj, reroute_point, destination, blockages, pathfinder)
            full_plan.append({"train_info": train_info, "decision": decision, "result": result, "reroute_point": reroute_point})
        return full_plan
