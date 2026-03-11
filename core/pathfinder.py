import csv
import heapq
from collections import defaultdict

class Edge:
    def __init__(self, from_node, to_node, base_travel_time):
        self.from_node = from_node
        self.to_node = to_node
        self.base_travel_time = base_travel_time

class Train:
    def __init__(self, priority):
        self.priority = priority

class RailwayPathfinder:
    def __init__(self, file_path: str):
        self.adj = defaultdict(list)
        self.nodes = set()
        self._build_graph_from_csv(file_path)

    def _build_graph_from_csv(self, file_path: str):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("base_time_minutes"):
                        from_sta = row["from_station"]
                        to_sta = row["to_station"]
                        self.nodes.add(from_sta)
                        self.nodes.add(to_sta)
                        edge = Edge(from_sta, to_sta, float(row["base_time_minutes"]))
                        self.adj[from_sta].append(edge)
        except FileNotFoundError:
            print(f"Network file {file_path} not found.")

    def find_k_shortest_paths(self, source: str, target: str, train: Train, K: int = 3, blockages=None):
        if blockages is None: blockages = []
        
        # Simple Dijkstra implementation without advanced weighting
        temp_adj = defaultdict(list)
        for u, edges in self.adj.items():
            for e in edges:
                if (u, e.to_node) not in blockages and (e.to_node, u) not in blockages:
                    temp_adj[u].append(e)

        dist = {n: float('inf') for n in self.nodes}
        if source not in self.nodes: return []
        dist[source] = 0
        prev = {n: None for n in self.nodes}
        pq = [(0, source)]

        while pq:
            d, u = heapq.heappop(pq)
            if u == target: break
            if d > dist.get(u, float('inf')): continue
            
            for edge in temp_adj.get(u, []):
                v = edge.to_node
                if dist[u] + edge.base_travel_time < dist.get(v, float('inf')):
                    dist[v] = dist[u] + edge.base_travel_time
                    prev[v] = u
                    heapq.heappush(pq, (dist[v], v))
                    
        if dist.get(target) == float('inf'): return []
        path = []
        curr = target
        while curr is not None:
            path.append(curr)
            curr = prev.get(curr)
        path.reverse()
        
        # Return single best path in Yen format mock
        return [{'cost': dist[target], 'path': path}]
