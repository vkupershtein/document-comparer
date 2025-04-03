"""
Module to build a specific graph for document headers and
find best pathways in it
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

@dataclass
class Element:
    position: int
    value: str    
    visited: bool
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def compare_fct(cls, x: str):
        sections = (s.split(".") for s in x.split("-"))
        tuple_list = []
        for subsection in sections:
            num_list = []
            for item in subsection:
                try:
                    num_list.append(int(item))
                except ValueError:
                    num_list.append(0)
            tuple_list.append(tuple(num_list))
        return tuple(tuple_list)
    
    def __eq__(self, other):
        return self.value == other.value and self.position==other.position
    
    def __lt__(self, other):
        return self.compare_fct(self.value) < self.compare_fct(other.value)

    def __le__(self, other):
        return self.compare_fct(self.value) <= self.compare_fct(other.value)

    def __gt__(self, other):
        return self.compare_fct(self.value) > self.compare_fct(other.value)

    def __ge__(self, other):
        return self.compare_fct(self.value) >= self.compare_fct(other.value)                    

    def __hash__(self):
        return hash((self.position, self.value))

class GraphBuilder:
    """
    Graph builder class
    """

    def __init__(self, sequence: List[Tuple[str, Dict]]):
        self.graph, self.root_elements = self.make_full_graph(sequence)

    @classmethod
    def make_full_graph(cls, sequence: List[Tuple[str, Dict]]) -> Tuple[Dict[Element, List[Element]], List[Element]]:
        element_sequence = cls.initialize_sequence(sequence)
        graph: Dict[Element, List[Element]] = {}
        root_elements: List[Element] = []
        for element in element_sequence:
            graph_part = cls.find_larger_neighbours(element, element_sequence)
            if graph_part:
                graph = graph | graph_part
                root_elements.append(element)       
            
        return graph, root_elements

    @classmethod
    def initialize_sequence(cls, sequence: List[Tuple[str, Dict]]):
        return [Element(i, value, False, metadata) for i, (value, metadata) in enumerate(sequence)]

    @classmethod
    def find_larger(cls, element: Element, subsequence: List[Element], start_pos=0):
        for i, item in enumerate(subsequence):
            if item.value > element.value and i >= start_pos:
                return i
        return None

    @classmethod
    def find_smaller(cls, root_element: Element, element: Element, subsequence: List[Element], start_pos: int=0):
        for i, item in enumerate(subsequence):
            if root_element.value < item.value < element.value and i >= start_pos:
                return i
        return None            

    @classmethod
    def find_larger_neighbours(cls, element: Element, sequence: List[Element]):    
        if len(sequence) == 0 or element.visited:
            return {}
        element.visited = True
        graph: Dict[Element, List[Element]] = {}    
        subsequence = sequence.copy()
        neighbours: List[Element] = []    
        pos = cls.find_larger(element, subsequence, element.position+1)    
        if pos is None:
            return graph
        current_neighbour = subsequence[pos]
        neighbours.append(current_neighbour)
        current_position = pos+1        
        while current_position < len(subsequence):
            pos = cls.find_smaller(element, current_neighbour, subsequence, current_position)
            if pos is None:
                break        
            neighbour = subsequence[pos]
            neighbours.append(neighbour)        
            current_neighbour = neighbour
            current_position = pos+1
        graph[element] = neighbours
        for neighbour_element in neighbours:
            graph = graph | cls.find_larger_neighbours(neighbour_element, subsequence)
        return graph
    
    @classmethod
    def find_best_path(cls, paths: List[List[Element]]) -> List[Element]:
        if len(paths) == 0:
            return []
        best_path = paths[0]
        best_path_range = best_path[-1].position - best_path[0].position
        for path in paths[1:]:
            if len(path) > len(best_path):
                best_path = path
            elif len(path) == len(best_path):
                path_range = path[-1].position - path[0].position
                if path_range < best_path_range:
                    best_path = path
        return best_path    
    
    def find_paths(self, start: Element, path=None, all_paths=None) -> List[List[Element]]:
        if path is None:
            path = []
        if all_paths is None:
            all_paths = []
        
        path = path + [start]        
        
        if start not in self.graph or not self.graph[start]:
            all_paths.append(path)
            return all_paths
        
        for neighbor in self.graph[start]:
            self.find_paths(neighbor, path, all_paths)
        
        return all_paths   
    
    def find_best_path_in_sequence(self) -> List[Element]:
        path_candidates: List[List[Element]] = []
        for root_element in self.root_elements:
            candidate = self.find_best_path(self.find_paths(root_element))
            path_candidates.append(candidate)
        return self.find_best_path(path_candidates)    
