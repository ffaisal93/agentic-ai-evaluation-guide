# Topic 1: Agentic AI Fundamentals

## What You'll Learn

This topic teaches you the fundamentals of agentic AI:
- What is an AI agent?
- Agent architectures and components
- How agents differ from traditional LLMs
- Planning, action, observation loop
- Memory and state management

## Why We Need This

### Business Need
Companies are building AI agents to:
- **Automate complex tasks**: Multi-step workflows that require reasoning
- **Interact with systems**: APIs, databases, tools
- **Make decisions**: Autonomous decision-making
- **Handle dynamic environments**: Adapt to changing conditions

### Technical Need
- **Understanding agents**: Need to know what we're evaluating
- **Architecture knowledge**: Different architectures need different evaluation
- **Component understanding**: Each component (memory, tools, planning) needs testing

### Real-World Impact
Without understanding fundamentals:
- ❌ Can't design proper evaluations
- ❌ Don't know what to measure
- ❌ Miss critical components
- ❌ Evaluate the wrong things

## Industry Use Cases

### 1. **Customer Support Agents**
**Company**: Zendesk, Intercom, Drift
**Use Case**: 
- Agent handles customer queries
- Uses tools (CRM, knowledge base)
- Makes decisions (escalate, resolve)
- Learns from interactions

**Example:**
```python
agent = CustomerSupportAgent()
response = agent.handle_query("How do I return an item?")
# Agent: Plans → Uses CRM tool → Retrieves policy → Responds
```

### 2. **Code Generation Agents**
**Company**: GitHub Copilot, Cursor, v0
**Use Case**:
- Agent writes code based on requirements
- Uses tools (compiler, linter, tests)
- Iterates based on feedback
- Handles errors

**Example:**
```python
agent = CodeGenerationAgent()
code = agent.generate("Create a REST API endpoint")
# Agent: Plans → Writes code → Tests → Fixes errors → Completes
```

### 3. **Research Agents**
**Company**: Perplexity, Elicit, Consensus
**Use Case**:
- Agent researches topics
- Uses search tools, databases
- Synthesizes information
- Provides citations

**Example:**
```python
agent = ResearchAgent()
report = agent.research("Latest LLM architectures")
# Agent: Plans → Searches → Reads papers → Synthesizes → Reports
```

### 4. **Trading Agents**
**Company**: Quant firms, trading platforms
**Use Case**:
- Agent makes trading decisions
- Uses market data tools
- Analyzes patterns
- Executes trades

**Example:**
```python
agent = TradingAgent()
decision = agent.analyze_market("AAPL")
# Agent: Plans → Analyzes data → Makes decision → Executes
```

### 5. **Content Creation Agents**
**Company**: Jasper, Copy.ai, Writesonic
**Use Case**:
- Agent creates content
- Uses research tools
- Iterates based on feedback
- Publishes content

**Example:**
```python
agent = ContentAgent()
article = agent.create("Blog post about AI")
# Agent: Plans → Researches → Writes → Edits → Publishes
```

## Industry-Standard Boilerplate Code

### Basic Agent Implementation (Industry Standard)

```python
"""
Basic Agent Implementation
Used by: LangChain, AutoGPT, custom agent frameworks
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

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

class Agent:
    """
    Basic agent implementation following planning-action-observation loop
    Industry standard pattern used by all agent frameworks
    """
    
    def __init__(
        self,
        name: str,
        tools: List[Any],
        memory: Optional[Any] = None,
        max_iterations: int = 10
    ):
        self.name = name
        self.tools = {tool.name: tool for tool in tools}
        self.memory = memory
        self.max_iterations = max_iterations
        self.state = AgentState.PLANNING
        self.history: List[Dict[str, Any]] = []
    
    def plan(self, goal: str) -> List[AgentAction]:
        """
        Planning phase: Decide what actions to take
        Industry standard: LLM-based planning
        """
        # In production, this would use an LLM to generate a plan
        # For now, simplified example
        plan = [
            AgentAction(
                tool_name="search",
                parameters={"query": goal},
                reasoning=f"Need to search for information about {goal}"
            )
        ]
        return plan
    
    def act(self, action: AgentAction) -> AgentObservation:
        """
        Action phase: Execute the planned action
        Industry standard: Tool execution with error handling
        """
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
        """
        Observation phase: Process the result and decide next steps
        Industry standard: Update state, check completion
        """
        self.history.append({
            "observation": observation,
            "timestamp": self._get_timestamp()
        })
        
        if observation.success:
            # Check if goal is achieved
            if self._is_goal_achieved(observation):
                self.state = AgentState.COMPLETED
                return True
            else:
                self.state = AgentState.PLANNING  # Re-plan
                return False
        else:
            # Handle error, might need to replan
            self.state = AgentState.ERROR
            return False
    
    def run(self, goal: str) -> Dict[str, Any]:
        """
        Main execution loop: Planning → Action → Observation
        Industry standard: Iterative loop with max iterations
        """
        self.state = AgentState.PLANNING
        self.history = []
        iterations = 0
        
        while iterations < self.max_iterations:
            if self.state == AgentState.COMPLETED:
                break
            
            if self.state == AgentState.PLANNING:
                # Plan next actions
                actions = self.plan(goal)
                self.state = AgentState.ACTING
            
            elif self.state == AgentState.ACTING:
                # Execute actions
                for action in actions:
                    observation = self.act(action)
                    should_continue = self.observe(observation)
                    if not should_continue:
                        break
            
            elif self.state == AgentState.ERROR:
                # Handle error, replan
                self.state = AgentState.PLANNING
            
            iterations += 1
        
        return {
            "success": self.state == AgentState.COMPLETED,
            "iterations": iterations,
            "history": self.history,
            "final_state": self.state.value
        }
    
    def _is_goal_achieved(self, observation: AgentObservation) -> bool:
        """Check if goal is achieved based on observation"""
        # Simplified: In production, this would use LLM to evaluate
        return observation.result is not None
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()


# Example Tool Interface
class Tool:
    """Base class for tools agents can use"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters"""
        raise NotImplementedError


# Example: Search Tool
class SearchTool(Tool):
    """Example search tool"""
    
    def __init__(self):
        super().__init__(
            name="search",
            description="Search for information"
        )
    
    def execute(self, query: str) -> str:
        """Execute search"""
        # In production, this would call a real search API
        return f"Search results for: {query}"


# Usage Example
if __name__ == "__main__":
    # Create tools
    search_tool = SearchTool()
    
    # Create agent
    agent = Agent(
        name="ResearchAgent",
        tools=[search_tool],
        max_iterations=5
    )
    
    # Run agent
    result = agent.run("What is agentic AI?")
    
    print(f"Success: {result['success']}")
    print(f"Iterations: {result['iterations']}")
    print(f"Final State: {result['final_state']}")
```

### Agent with Memory (Industry Standard)

```python
"""
Agent with Memory
Used by: Production agents that need to remember context
"""
from typing import List, Dict
from collections import deque

class AgentMemory:
    """
    Memory system for agents
    Industry standard: Short-term and long-term memory
    """
    
    def __init__(self, max_short_term: int = 10):
        self.short_term = deque(maxlen=max_short_term)
        self.long_term: List[Dict] = []
    
    def add(self, item: Dict):
        """Add item to short-term memory"""
        self.short_term.append(item)
    
    def get_context(self) -> List[Dict]:
        """Get recent context for agent"""
        return list(self.short_term)
    
    def save_to_long_term(self, item: Dict):
        """Save important items to long-term memory"""
        self.long_term.append(item)


class AgentWithMemory(Agent):
    """Agent with memory capabilities"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.memory is None:
            self.memory = AgentMemory()
    
    def plan(self, goal: str) -> List[AgentAction]:
        """Plan using memory context"""
        context = self.memory.get_context()
        # Use context in planning (simplified)
        return super().plan(goal)
    
    def observe(self, observation: AgentObservation) -> bool:
        """Store observations in memory"""
        self.memory.add({
            "observation": observation,
            "timestamp": self._get_timestamp()
        })
        return super().observe(observation)
```

## Key Concepts Explained

### Planning-Action-Observation Loop

```
1. PLAN: Agent decides what to do
   ↓
2. ACT: Agent executes action using tools
   ↓
3. OBSERVE: Agent sees result
   ↓
4. DECIDE: Goal achieved? If not, back to PLAN
```

### Agent Components

1. **Planning Module**: Decides what actions to take
2. **Action Module**: Executes actions using tools
3. **Observation Module**: Processes results
4. **Memory**: Stores context and history
5. **Tools**: External capabilities (APIs, functions)

## Exercises

1. **Create a simple agent**: Implement basic agent with one tool
2. **Add memory**: Implement memory system
3. **Multiple tools**: Add multiple tools to agent
4. **Error handling**: Add robust error handling
5. **State management**: Implement proper state transitions

## Next Steps

- **Topic 2**: Learn evaluation frameworks
- **Topic 3**: Understand metrics and benchmarks

## Further Reading

- [LangChain Agents](https://python.langchain.com/docs/modules/agents/)
- [AutoGPT Architecture](https://github.com/Significant-Gravitas/AutoGPT)
- [ReAct Paper](https://arxiv.org/abs/2210.03629)

