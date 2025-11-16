"""
Orchestrator - Multi-agent pipeline using ADK patterns.
Manages agent graph, session service, memory, tools, and tracing.
"""
import uuid
from typing import Any, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.agents.intent_agent import IntentAgent
from src.agents.task_agent import TaskAgent
from src.agents.meal_agent import MealAgent
from src.agents.budget_agent import BudgetAgent
from src.agents.scheduler_agent import SchedulerAgent
from src.agents.coordinator_agent import CoordinatorAgent
from src.agents.verifier_agent import VerifierAgent

from src.memory.session_memory import session_service
from src.memory.longterm_memory import longterm_memory
from src.utils.logger import logger


class AgentGraph:
    """
    ADK-compatible agent graph for managing agent execution flow.
    """
    
    def __init__(self):
        """Initialize agent graph."""
        self.agents = {}
        self.execution_trace = []
    
    def add_agent(self, name: str, agent: Any) -> None:
        """Add agent to graph."""
        self.agents[name] = agent
    
    def execute_sequential(self, agent_names: list, initial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agents sequentially.
        
        Args:
            agent_names: List of agent names in execution order
            initial_data: Initial input data
            
        Returns:
            Final result dictionary
        """
        result = initial_data
        for agent_name in agent_names:
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                step_result = agent.process(result)
                result.update(step_result)
                self.execution_trace.append({
                    "agent": agent_name,
                    "result": step_result
                })
        return result
    
    def execute_parallel(
        self,
        agent_names: list,
        shared_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute agents in parallel.
        
        Args:
            agent_names: List of agent names to execute in parallel
            shared_data: Shared input data for all agents
            
        Returns:
            Dictionary with results from all agents
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=len(agent_names)) as executor:
            futures = {}
            for agent_name in agent_names:
                if agent_name in self.agents:
                    agent = self.agents[agent_name]
                    future = executor.submit(agent.process, shared_data)
                    futures[future] = agent_name
            
            for future in as_completed(futures):
                agent_name = futures[future]
                try:
                    result = future.result()
                    results[agent_name] = result
                    self.execution_trace.append({
                        "agent": agent_name,
                        "result": result
                    })
                except Exception as e:
                    logger.log_event(
                        "AgentGraph",
                        "parallel_execution_error",
                        {"agent": agent_name, "error": str(e)},
                        shared_data.get("session_id")
                    )
                    results[agent_name] = {"error": str(e), "agent": agent_name}
        
        return results


class Orchestrator:
    """
    Main orchestrator for multi-agent pipeline.
    Manages ADK session service, agent graph, memory, tools, and tracing.
    """
    
    def __init__(self):
        """Initialize orchestrator."""
        self.graph = AgentGraph()
        self.session_service = session_service
        self.longterm_memory = longterm_memory
    
    def run_pipeline(
        self,
        user_text: str,
        session_id: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run the complete multi-agent pipeline.
        
        Pipeline flow:
        1. IntentAgent (extract goals/constraints)
        2. Parallel: TaskAgent, MealAgent, BudgetAgent
        3. SchedulerAgent (combine and resolve conflicts)
        4. CoordinatorAgent (merge and optimize)
        5. VerifierAgent (final validation)
        
        Args:
            user_text: User input text
            session_id: Optional session identifier (generated if not provided)
            
        Returns:
            Complete pipeline result with plan and trace
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        logger.log_event(
            "Orchestrator",
            "pipeline_started",
            {"user_text": user_text, "session_id": session_id},
            session_id
        )
        
        # Initialize session
        session = self.session_service.get_session(session_id)
        self.session_service.add_query(session_id, user_text)
        
        # Initialize agents with session ID and API key
        intent_agent = IntentAgent(session_id, api_key=api_key)
        task_agent = TaskAgent(session_id, api_key=api_key)
        meal_agent = MealAgent(session_id, api_key=api_key)
        budget_agent = BudgetAgent(session_id, api_key=api_key)
        scheduler_agent = SchedulerAgent(session_id, api_key=api_key)
        coordinator_agent = CoordinatorAgent(session_id, api_key=api_key)
        verifier_agent = VerifierAgent(session_id, api_key=api_key)
        
        # Build agent graph
        self.graph.add_agent("intent", intent_agent)
        self.graph.add_agent("task", task_agent)
        self.graph.add_agent("meal", meal_agent)
        self.graph.add_agent("budget", budget_agent)
        self.graph.add_agent("scheduler", scheduler_agent)
        self.graph.add_agent("coordinator", coordinator_agent)
        self.graph.add_agent("verifier", verifier_agent)
        
        try:
            # Step 1: Intent extraction
            logger.log_event(
                "Orchestrator",
                "step_1_intent",
                {"step": "extracting_intent"},
                session_id
            )
            intent_result = intent_agent.process(user_text)
            
            # Step 2: Parallel execution of Task, Meal, and Budget agents
            logger.log_event(
                "Orchestrator",
                "step_2_parallel",
                {"step": "parallel_agents"},
                session_id
            )
            
            # Prepare shared data for parallel agents
            shared_data = {"intent": intent_result.get("intent", {})}
            
            # Execute in parallel
            parallel_results = self.graph.execute_parallel(
                ["task", "meal"],
                shared_data
            )
            
            task_result = parallel_results.get("task", {})
            meal_result = parallel_results.get("meal", {})
            
            # Budget agent needs meal data, so run after meal agent
            budget_result = budget_agent.process(intent_result, meal_result)
            
            # Step 3: Scheduling
            logger.log_event(
                "Orchestrator",
                "step_3_scheduling",
                {"step": "scheduling"},
                session_id
            )
            schedule_result = scheduler_agent.process(
                task_result,
                meal_result,
                intent_result
            )
            
            # Step 4: Coordination
            logger.log_event(
                "Orchestrator",
                "step_4_coordination",
                {"step": "coordinating"},
                session_id
            )
            coordinator_result = coordinator_agent.process(
                intent_result,
                task_result,
                meal_result,
                budget_result,
                schedule_result
            )
            
            # Step 5: Verification
            logger.log_event(
                "Orchestrator",
                "step_5_verification",
                {"step": "verifying"},
                session_id
            )
            verification_result = verifier_agent.process(coordinator_result)
            
            # Compile final result
            final_result = {
                "session_id": session_id,
                "user_input": user_text,
                "plan": coordinator_result.get("optimized_plan", {}).get("plan", {}),
                "verification": verification_result.get("verification", {}),
                "evaluation": coordinator_result.get("optimized_plan", {}).get("evaluation", {}),
                "recommendations": coordinator_result.get("optimized_plan", {}).get("recommendations", []),
                "trace": self.graph.execution_trace,
                "status": "success"
            }
            
            # Save plan state
            self.session_service.save_plan_state(session_id, "final_plan", final_result)
            
            # Update long-term memory
            self.longterm_memory.add_history({
                "session_id": session_id,
                "goals": intent_result.get("intent", {}).get("goals", []),
                "plan_score": coordinator_result.get("optimized_plan", {}).get("score", 0.0)
            })
            
            logger.log_event(
                "Orchestrator",
                "pipeline_completed",
                {"session_id": session_id, "status": "success"},
                session_id
            )
            
            return final_result
            
        except Exception as e:
            logger.log_event(
                "Orchestrator",
                "pipeline_error",
                {"error": str(e), "session_id": session_id},
                session_id
            )
            return {
                "session_id": session_id,
                "user_input": user_text,
                "status": "error",
                "error": str(e),
                "trace": self.graph.execution_trace
            }


# Global orchestrator instance
orchestrator = Orchestrator()

