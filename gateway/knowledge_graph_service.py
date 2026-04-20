import json
import os
import networkx as nx
from typing import List, Dict, Any, Optional
from core.logger import get_logger

logger = get_logger(__name__)

class KnowledgeGraphService:
    """
    Service for querying the graphifyy-generated codebase graph.
    Provides BFS traversal and node lookup to enrich agent reasoning.
    """
    def __init__(self, graph_path: str = "graphify-out/graph.json"):
        self.graph_path = graph_path
        self.graph = None
        self.nx_graph = None
        self._load_graph()

    def _load_graph(self):
        """Load the graph.json file and initialize NetworkX object."""
        if not os.path.exists(self.graph_path):
            logger.warning(f"Knowledge Graph not found at {self.graph_path}. Run 'graphify update .' first.")
            return

        try:
            with open(self.graph_path, "r") as f:
                data = json.load(f)
                self.graph = data
                
                # Convert to NetworkX for easier traversal
                self.nx_graph = nx.Graph()
                for node in data.get("nodes", []):
                    self.nx_graph.add_node(node["id"], **node)
                for edge in data.get("links", data.get("edges", [])):
                    self.nx_graph.add_edge(edge["source"], edge["target"], **edge)
                
                logger.info(f"Loaded Knowledge Graph: {len(self.nx_graph.nodes)} nodes, {len(self.nx_graph.edges)} edges.")
        except Exception as e:
            logger.error(f"Failed to load Knowledge Graph: {e}")

    def query_related_nodes(self, node_label: str, depth: int = 1) -> List[Dict[str, Any]]:
        """Find nodes related to a specific label (function name, file, etc.)."""
        if not self.nx_graph:
            return []

        # Find the node ID by label
        target_id = None
        for n, d in self.nx_graph.nodes(data=True):
            if d.get("label") == node_label or d.get("norm_label") == node_label.lower():
                target_id = n
                break
        
        if not target_id:
            return []

        # Get ego graph (neighbors within depth)
        try:
            ego = nx.ego_graph(self.nx_graph, target_id, radius=depth)
            results = []
            for n, d in ego.nodes(data=True):
                if n != target_id:
                    results.append({
                        "id": n,
                        "label": d.get("label"),
                        "type": d.get("file_type"),
                        "file": d.get("source_file"),
                        "location": d.get("source_location")
                    })
            return results
        except Exception:
            return []

    def get_code_context(self, search_term: str) -> str:
        """Helper for agents to get code architecture context."""
        nodes = self.query_related_nodes(search_term, depth=1)
        if not nodes:
            return f"No direct graph relationships found for '{search_term}'."
        
        context = f"Codebase Relationships for '{search_term}':\n"
        for n in nodes[:10]:
            context += f"- {n['label']} ({n['type']}) in {os.path.basename(n['file'] or '')}\n"
        return context

knowledge_graph = KnowledgeGraphService()
