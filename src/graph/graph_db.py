from typing import List, Optional, Dict
from datetime import datetime
import uuid
import json

class GraphDatabase:
    def __init__(self):
        self.nodes = Dict[str, Dict] = {}
        self.edges = List[Dict] = []

    def add_node(self, node_type: str, properties: Dict) -> str:
        node_id = str(uuid.uuid4())
        self.nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            "properties": properties,
            "created_at": datetime.now().isoformat()
        }

        return node_id

    def add_edge(self, from_id: str, to_id: str, relation: str, properties: Optional[Dict] = None):
        if from_id not in self.nodes:
            raise ValueError(f"Node with id {from_id} not found.")

        if to_id not in self.nodes:
            raise ValueError(f"Node with id {to_id} not found.")

        self.edges.append({
            "from": from_id,
            "to": to_id,
            "relation": relation,
            "properties": properties or {},
            "created_at": datetime.now().isoformat()
        })

    def get_node(self, node_id: str) -> Optional[Dict]:
        return self.nodes.get(node_id)
    
    def get_edges(self, node_id: str) -> List[Dict]:
        return [e for e in self.edges if e["from"] == node_id or e["to"] == node_id]
    
    def get_neighbors(self, node_id: str, relation: Optional[str] = None) -> List[Dict]:
        neighbors = []
        for edge in self.edges:
            if edge["from"] == node_id:
                if not relation or edge["relation"] == relation:
                    neighbors.append(self.nodes[edge["to"]])
            elif edge["to"] == node_id:
                if not relation or edge["relation"] == relation:
                    neighbors.append(self.nodes[edge["from"]])
        return neighbors
    
    def query(self, node_type: str, filters: Dict) -> List[Dict]:
        results = []
        for node in self.nodes.values():
            if node["type"] != node_type:
                continue
            
            match = True
            for key, value in filters.items():
                if node["properties"].get(key) != value:
                    match = False
                    break
            
            if match:
                results.append(node)
        return results
    
    def save(self, filename: str = "data/graph_data.json"):
        data = {"nodes": self.nodes, "edges": self.edges}
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load(self, filename: str = "data/graph_data.json"):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.nodes = data["nodes"]
            self.edges = data["edges"]
            return True
        except FileNotFoundError:
            print(f"File {filename} not found.")
            return False


        