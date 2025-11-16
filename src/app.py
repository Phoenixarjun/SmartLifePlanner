"""
Streamlit Web App for Smart Life Planner.
Main entry point for the application.
"""
import streamlit as st
import json
from typing import Dict, Any

from src.orchestrator import orchestrator
from src.utils.logger import logger
from src.utils.llm_service import llm_service


def format_plan_display(plan: Dict[str, Any]) -> str:
    """
    Format plan safely for display.
    Prevents crashes when scheduler returns strings instead of dict events.
    """
    if not plan:
        return "No plan generated."

    output = []

    # Goals
    goals = plan.get("goals", [])
    if goals:
        output.append("## 🎯 Goals")
        for goal in goals:
            output.append(f"- {goal}")
        output.append("")

    # Schedule
    schedule = plan.get("schedule", {})
    if schedule:
        output.append("## 📅 Weekly Schedule")

        for day, events in schedule.items():
            output.append(f"### {day}")

            if not isinstance(events, list):
                output.append(f"- (invalid schedule entry)")
                continue

            for event in events:
                # If event is accidentally a string → convert to dict
                if isinstance(event, str):
                    event = {
                        "title": event,
                        "type": "task",
                        "start_time": "N/A",
                        "duration_minutes": 0
                    }

                # Fallback if event is NONE or corrupted
                if not isinstance(event, dict):
                    output.append(f"- (invalid event)")
                    continue

                event_type = event.get("type", "task")
                icon = "🍽️" if event_type == "meal" else "✓"

                output.append(
                    f"{icon} **{event.get('title', 'Event')}** "
                    f"({event.get('start_time', 'N/A')}, "
                    f"{event.get('duration_minutes', 0)} min)"
                )

            output.append("")

    # Budget
    budget = plan.get("budget", {})
    if budget:
        output.append("## 💰 Budget")
        total = budget.get("total", 0.0)
        within_budget = budget.get("within_budget", True)
        status = "✅" if within_budget else "⚠️"
        output.append(f"{status} Total: ${total:.2f}")

        shopping_list = budget.get("shopping_list", [])
        if shopping_list:
            output.append("\n**Shopping List:**")
            for item in shopping_list[:10]:
                price = budget.get("item_prices", {}).get(item, 0.0)
                output.append(f"- {item} (${price:.2f})")
        output.append("")

    # Tasks
    tasks = plan.get("tasks", [])
    if tasks:
        output.append("## ✅ Tasks")
        for task in tasks[:5]:
            if isinstance(task, dict):
                output.append(
                    f"- {task.get('title', 'Task')} "
                    f"({task.get('duration_minutes', 0)} min, "
                    f"{task.get('priority', 'medium')} priority)"
                )
            else:
                output.append(f"- {task}")
        output.append("")

    # Meals
    meals = plan.get("meals", [])
    if meals:
        output.append("## 🍽️ Meal Plan")
        for day_plan in meals[:3]:
            if not isinstance(day_plan, dict):
                continue

            day = day_plan.get("day", "Day")
            output.append(f"### {day}")

            for meal in day_plan.get("meals", []):
                if isinstance(meal, dict):
                    output.append(
                        f"- {meal.get('name', 'Meal')} "
                        f"({meal.get('type', 'meal')}, "
                        f"{meal.get('calories', 0)} cal)"
                    )
        output.append("")

    return "\n".join(output)

def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Smart Life Planner",
        page_icon="📅",
        layout="wide"
    )
    
    st.title("📅 Smart Life Planner")
    st.markdown(
        "An intelligent multi-agent system for planning your week: "
        "tasks, meals, budget, and schedule optimization."
    )
    
    # Sidebar for settings
    with st.sidebar:
        st.header("Settings")
        
        # Gemini API Key input
        st.subheader("🔑 Gemini API Key")
        st.markdown("Enter your Google Gemini API key:")
        st.markdown("Get your API key from: [Google AI Studio](https://makersuite.google.com/app/apikey)")
        
        # Initialize session state for API key
        if "gemini_api_key" not in st.session_state:
            st.session_state.gemini_api_key = ""
        
        # API key input
        api_key_input = st.text_input(
            "API Key",
            type="password",
            value=st.session_state.gemini_api_key,
            help="Enter your Gemini API key and click Save",
            key="api_key_input"
        )
        
        # Save button
        if st.button("💾 Save API Key", type="primary"):
            if api_key_input and api_key_input.strip():
                st.session_state.gemini_api_key = api_key_input.strip()
                st.success("✅ API key saved!")
                st.rerun()
            else:
                st.warning("⚠️ Please enter an API key")
        
        # Show status
        if st.session_state.gemini_api_key:
            st.info(f"✅ API key saved (length: {len(st.session_state.gemini_api_key)})")
        else:
            st.warning("⚠️ No API key saved. Enter and save your API key to generate plans.")
        
        st.markdown("---")
        show_trace = st.checkbox("Show execution trace", value=False)
        show_logs = st.checkbox("Show logs", value=False)
    
    # Main input area
    st.header("Enter Your Planning Request")
    user_input = st.text_area(
        "Describe what you want to plan:",
        placeholder=(
            "Example: 'Plan my week with exercise, healthy meals, "
            "and grocery shopping. Budget is $100. I'm vegetarian.'"
        ),
        height=100
    )
    
    if st.button("🚀 Generate Plan", type="primary"):
        if not user_input.strip():
            st.warning("Please enter a planning request.")
        else:
            # Get API key from session state
            api_key = st.session_state.get("gemini_api_key", "")
            
            if not api_key:
                st.error("❌ Please enter and save your Gemini API key in the sidebar first.")
            else:
                with st.spinner("Generating your plan... This may take a moment."):
                    # Run pipeline with API key (will validate during execution)
                    result = orchestrator.run_pipeline(user_input, api_key=api_key)
                
                # Display results
                if result.get("status") == "success":
                    st.success("✅ Plan generated successfully!")
                    
                    # Main plan display
                    plan = result.get("plan", {})
                    st.markdown(format_plan_display(plan))
                    
                    # Verification
                    verification = result.get("verification", {})
                    if verification:
                        st.header("🔍 Verification")
                        is_valid = verification.get("is_valid", False)
                        status_icon = "✅" if is_valid else "⚠️"
                        st.markdown(f"{status_icon} **Plan Status:** {'VALID' if is_valid else 'INVALID'}")
                        
                        if verification.get("verification_summary"):
                            with st.expander("Verification Details"):
                                st.text(verification.get("verification_summary"))
                    
                    # Recommendations
                    recommendations = result.get("recommendations", [])
                    if recommendations:
                        st.header("💡 Recommendations")
                        for rec in recommendations:
                            st.info(rec)
                    
                    # Evaluation metrics
                    evaluation = result.get("evaluation", {})
                    if evaluation:
                        st.header("📊 Evaluation Metrics")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric(
                                "Overall Score",
                                f"{evaluation.get('overall_score', 0.0):.2%}"
                            )
                        with col2:
                            st.metric(
                                "Goal Satisfaction",
                                f"{evaluation.get('goal_satisfaction_score', 0.0):.2%}"
                            )
                        with col3:
                            st.metric(
                                "Constraint Compliance",
                                f"{evaluation.get('constraint_compliance', 0.0):.2%}"
                            )
                        with col4:
                            budget_dev = evaluation.get("budget_deviation", 0.0)
                            st.metric(
                                "Budget Deviation",
                                f"{budget_dev:.1f}%" if budget_dev > 0 else "0%"
                            )
                    
                    # Execution trace
                    if show_trace:
                        st.header("🔗 Execution Trace")
                        trace = result.get("trace", [])
                        for i, step in enumerate(trace, 1):
                            with st.expander(f"Step {i}: {step.get('agent', 'Unknown')}"):
                                st.json(step.get("result", {}))
                    
                    # Logs
                    if show_logs:
                        st.header("📝 Logs")
                        session_id = result.get("session_id")
                        if session_id:
                            logs = logger.trace_session(session_id)
                            if logs:
                                st.json(logs)
                            else:
                                st.info("No logs available for this session.")
                
                else:
                    st.error(f"❌ Error generating plan: {result.get('error', 'Unknown error')}")
                    if show_trace:
                        st.json(result)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "**Smart Life Planner** - Multi-agent planning system with "
        "ADK architecture, tools, memory, and observability."
    )


if __name__ == "__main__":
    main()

