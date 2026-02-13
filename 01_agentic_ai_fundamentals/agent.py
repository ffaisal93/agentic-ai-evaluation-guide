"""
Basic Agent Implementation
Industry-standard agent following planning-action-observation pattern
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

class AgentState(Enum):
    PLANNING = "planning"
    ACTING = "acting"
    OBSERVING = "observing"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class AgentAction:
    """Represents an action the agent takes"""
    tool_name: str
    parameters: Dict[str, Any]
    reasoning: str

@dataclass
class AgentObservation:
    """Represents an observation from the environment"""
    result: Any
    success: bool
    error: Optional[str] = None

class Tool:
    """Base class for tools agents can use"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters"""
        raise NotImplementedError

class SearchTool(Tool):
    """Example search tool"""
    
    def __init__(self):
        super().__init__(
            name="search",
            description="Search for information"
        )
    
    def execute(self, query: str) -> str:
        """Execute search"""
        # Simulated search - in production would call real API
        return f"Search results for: {query}\n- Result 1\n- Result 2\n- Result 3"

class CalculatorTool(Tool):
    """Example calculator tool"""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            description="Perform calculations"
        )
    
    def execute(self, expression: str) -> float:
        """Execute calculation"""
        try:
            result = eval(expression)  # In production, use safe eval
            return float(result)
        except Exception as e:
            raise ValueError(f"Calculation error: {e}")

class Agent:
    """
    Basic agent implementation following planning-action-observation loop
    """
    
    def __init__(
        self,
        name: str,
        tools: List[Tool],
        max_iterations: int = 10
    ):
        self.name = name
        self.tools = {tool.name: tool for tool in tools}
        self.max_iterations = max_iterations
        self.state = AgentState.PLANNING
        self.history: List[Dict[str, Any]] = []
    
    def plan(self, goal: str) -> List[AgentAction]:
        """
        Planning phase: Decide what actions to take
        Simplified version - in production would use LLM
        """
        # Simple heuristic-based planning
        if "search" in goal.lower():
            return [
                AgentAction(
                    tool_name="search",
                    parameters={"query": goal},
                    reasoning=f"Need to search for information about: {goal}"
                )
            ]
        elif any(op in goal for op in ["+", "-", "*", "/", "calculate"]):
            return [
                AgentAction(
                    tool_name="calculator",
                    parameters={"expression": goal},
                    reasoning=f"Need to calculate: {goal}"
                )
            ]
        else:
            return [
                AgentAction(
                    tool_name="search",
                    parameters={"query": goal},
                    reasoning=f"Default action: search for {goal}"
                )
            ]
    
    def act(self, action: AgentAction) -> AgentObservation:
        """Action phase: Execute the planned action"""
        try:
            if action.tool_name not in self.tools:
                return AgentObservation(
                    result=None,
                    success=False,
                    error=f"Tool {action.tool_name} not found"
                )
            
            tool = self.tools[action.tool_name]
            result = tool.execute(**action.parameters)
            
            return AgentObservation(
                result=result,
                success=True
            )
        except Exception as e:
            return AgentObservation(
                result=None,
                success=False,
                error=str(e)
            )
    
    def observe(self, observation: AgentObservation) -> bool:
        """Observation phase: Process result and decide next steps"""
        self.history.append({
            "observation": observation,
            "timestamp": datetime.now().isoformat()
        })
        
        if observation.success:
            if self._is_goal_achieved(observation):
                self.state = AgentState.COMPLETED
                return True
            else:
                self.state = AgentState.PLANNING
                return False
        else:
            self.state = AgentState.ERROR
            return False
    
    def run(self, goal: str) -> Dict[str, Any]:
        """Main execution loop: Planning → Action → Observation"""
        self.state = AgentState.PLANNING
        self.history = []
        iterations = 0
        actions = []
        
        while iterations < self.max_iterations:
            if self.state == AgentState.COMPLETED:
                break
            
            if self.state == AgentState.PLANNING:
                actions = self.plan(goal)
                self.state = AgentState.ACTING
            
            elif self.state == AgentState.ACTING:
                for action in actions:
                    observation = self.act(action)
                    should_continue = self.observe(observation)
                    if not should_continue:
                        break
            
            elif self.state == AgentState.ERROR:
                self.state = AgentState.PLANNING
            
            iterations += 1
        
        return {
            "success": self.state == AgentState.COMPLETED,
            "iterations": iterations,
            "history": self.history,
            "final_state": self.state.value,
            "result": self.history[-1]["observation"].result if self.history else None
        }
    
    def _is_goal_achieved(self, observation: AgentObservation) -> bool:
        """Check if goal is achieved"""
        return observation.result is not None and observation.success

