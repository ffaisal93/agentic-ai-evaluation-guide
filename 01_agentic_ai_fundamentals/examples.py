"""
Examples of using the basic agent
Run this to see agents in action
"""

from agent import Agent, SearchTool, CalculatorTool

def example_1_simple_agent():
    """Example 1: Simple agent with search tool"""
    print("=" * 60)
    print("Example 1: Simple Agent with Search Tool")
    print("=" * 60)
    
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
    
    print(f"\nAgent: {agent.name}")
    print(f"Goal: What is agentic AI?")
    print(f"Success: {result['success']}")
    print(f"Iterations: {result['iterations']}")
    print(f"Final State: {result['final_state']}")
    print(f"\nResult:\n{result['result']}")
    print()

def example_2_calculator_agent():
    """Example 2: Agent with calculator tool"""
    print("=" * 60)
    print("Example 2: Agent with Calculator Tool")
    print("=" * 60)
    
    # Create tools
    calculator_tool = CalculatorTool()
    
    # Create agent
    agent = Agent(
        name="CalculatorAgent",
        tools=[calculator_tool],
        max_iterations=5
    )
    
    # Run agent
    result = agent.run("calculate 25 * 4 + 10")
    
    print(f"\nAgent: {agent.name}")
    print(f"Goal: calculate 25 * 4 + 10")
    print(f"Success: {result['success']}")
    print(f"Iterations: {result['iterations']}")
    print(f"Final State: {result['final_state']}")
    print(f"\nResult: {result['result']}")
    print()

def example_3_multi_tool_agent():
    """Example 3: Agent with multiple tools"""
    print("=" * 60)
    print("Example 3: Agent with Multiple Tools")
    print("=" * 60)
    
    # Create tools
    search_tool = SearchTool()
    calculator_tool = CalculatorTool()
    
    # Create agent
    agent = Agent(
        name="MultiToolAgent",
        tools=[search_tool, calculator_tool],
        max_iterations=5
    )
    
    # Run agent with calculation
    result = agent.run("calculate 100 / 4")
    
    print(f"\nAgent: {agent.name}")
    print(f"Goal: calculate 100 / 4")
    print(f"Success: {result['success']}")
    print(f"Iterations: {result['iterations']}")
    print(f"Final State: {result['final_state']}")
    print(f"\nResult: {result['result']}")
    print()

if __name__ == "__main__":
    print("\n🚀 Agentic AI Fundamentals - Examples\n")
    
    example_1_simple_agent()
    example_2_calculator_agent()
    example_3_multi_tool_agent()
    
    print("=" * 60)
    print("Examples complete!")
    print("=" * 60)

