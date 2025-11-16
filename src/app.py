import streamlit as st
import json
from typing import Dict, Any

from src.orchestrator import orchestrator
from src.utils.logger import logger
from src.utils.llm_service import llm_service

# Custom CSS for dark theme and enhanced styling
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary: #BB86FC;
        --primary-variant: #3700B3;
        --secondary: #03DAC6;
        --background: #121212;
        --surface: #1E1E1E;
        --error: #CF6679;
        --on-primary: #000000;
        --on-secondary: #000000;
        --on-background: #FFFFFF;
        --on-surface: #FFFFFF;
        --on-error: #000000;
    }
    
    /* Global styles */
    .main {
        background-color: var(--background);
        color: var(--on-background);
    }
    
    .stApp {
        background-color: var(--background);
        color: var(--on-background);
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: var(--primary) !important;
        font-weight: 600;
    }
    
    /* Sidebar */
    .css-1d391kg, .css-1lcbmhc {
        background-color: var(--surface) !important;
    }
    
    /* Buttons */
    .stButton button {
        background-color: var(--primary) !important;
        color: var(--on-primary) !important;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        background-color: var(--primary-variant) !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Text input */
    .stTextInput input, .stTextArea textarea {
        background-color: var(--surface) !important;
        color: var(--on-surface) !important;
        border: 1px solid #333 !important;
        border-radius: 8px;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 1px var(--primary) !important;
    }
    
    /* Metrics */
    .stMetric {
        background-color: var(--surface);
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid var(--primary);
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: var(--surface) !important;
        color: var(--on-surface) !important;
        border-radius: 8px 8px 0 0;
    }
    
    .streamlit-expanderContent {
        background-color: rgba(30, 30, 30, 0.8) !important;
        border-radius: 0 0 8px 8px;
    }
    
    /* Success, warning, error, info boxes */
    .stAlert {
        border-radius: 8px;
    }
    
    div[data-testid="stSidebarUserContent"] {
        padding: 2rem 1.5rem;
    }
    
    /* Custom cards */
    .custom-card {
        background-color: var(--surface);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid var(--secondary);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Progress bar */
    .stProgress > div > div > div {
        background-color: var(--primary);
    }
    
    /* Radio buttons */
    .stRadio > div {
        background-color: var(--surface);
        padding: 10px;
        border-radius: 8px;
    }
    
    /* Checkbox */
    .stCheckbox > label {
        color: var(--on-surface) !important;
    }
    
    /* Selectbox */
    .stSelectbox > div > div {
        background-color: var(--surface);
        color: var(--on-surface);
    }
    
    /* Divider */
    hr {
        border-color: #333;
        margin: 2rem 0;
    }
    
    /* Code blocks */
    .stCodeBlock {
        border-radius: 8px;
    }
    
    /* JSON viewer */
    .stJson {
        background-color: var(--surface);
        border-radius: 8px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

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
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Header with gradient
    st.markdown(
        """
<div style="
    background: linear-gradient(135deg, #000000 0%, #1F1F1F 100%);
    padding: 2rem;
    border-radius: 12px;
    margin-bottom: 2rem;
    box-shadow: 0 6px 16px rgba(0,0,0,0.45);
">
    <h1 style="color: #FFFFFF; margin: 0; text-align: center;">📅 Smart Life Planner</h1>
    <p style="
        color: #E0E0E0;
        text-align: center;
        font-size: 1.2rem;
        margin: 0.5rem 0 0 0;
    ">
        An intelligent multi-agent system for planning your week
    </p>
</div>
        """, 
        unsafe_allow_html=True
    )
    
    # Sidebar for settings
    with st.sidebar:
        # Sidebar header with styling
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #3700B3 0%, #03DAC6 100%);
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 1.5rem;
            ">
                <h2 style="color: #fff; margin: 0; text-align: center;">⚙️ Settings</h2>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Gemini API Key section
        st.markdown("### 🔑 Gemini API Key")
        st.markdown(
            "Enter your Google Gemini API key to get started. "
            "Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)"
        )
        
        # Initialize session state for API key
        if "gemini_api_key" not in st.session_state:
            st.session_state.gemini_api_key = ""
        
        # API key input
        api_key_input = st.text_input(
            "API Key",
            type="password",
            value=st.session_state.gemini_api_key,
            help="Enter your Gemini API key and click Save",
            key="api_key_input",
            placeholder="Paste your API key here..."
        )
        
        # Save button
        if st.button("💾 Save", type="primary", use_container_width=True):
                if api_key_input and api_key_input.strip():
                    st.session_state.gemini_api_key = api_key_input.strip()
                    st.success("✅ API key saved!")
                    st.rerun()
                else:
                    st.warning("⚠️ Please enter an API key")
        
        # API key status
        if st.session_state.gemini_api_key:
            st.markdown(
                f"""
                <div class="custom-card">
                    <p style="margin: 0; color: #03DAC6;">
                        ✅ API key saved (length: {len(st.session_state.gemini_api_key)})
                    </p>
                </div>
                """, 
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                """
                <div class="custom-card">
                    <p style="margin: 0; color: #CF6679;">
                        ⚠️ No API key saved. Enter and save your API key to generate plans.
                    </p>
                </div>
                """, 
                unsafe_allow_html=True
            )
        
        st.markdown("---")
        
        # Display options
        st.markdown("### 🔍 Display Options")
        show_trace = st.checkbox("Show execution trace", value=False)
        show_logs = st.checkbox("Show detailed logs", value=False)
        
        st.markdown("---")
        
        # Info section
        st.markdown("### ℹ️ About")
        st.markdown(
            """
            This Smart Life Planner uses a multi-agent system to:
            - 📅 Schedule your week
            - 🍽️ Plan your meals
            - 💰 Manage your budget
            - ✅ Organize your tasks
            
            All in one unified plan!
            """
        )
    
    # Main input area
    st.markdown(
        """
        <div class="custom-card">
            <h2>✨ Enter Your Planning Request</h2>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    user_input = st.text_area(
        "Describe what you want to plan:",
        placeholder=(
            "Example: 'Plan my week with exercise, healthy meals, "
            "and grocery shopping. Budget is $100. I'm vegetarian.'"
        ),
        height=120,
        label_visibility="collapsed"
    )
    
    # Generate plan button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        generate_clicked = st.button(
            "🚀 Generate Smart Plan", 
            type="primary", 
            use_container_width=True,
            disabled=not st.session_state.get("gemini_api_key")
        )
    
    if generate_clicked:
        if not user_input.strip():
            st.warning("Please enter a planning request.")
        else:
            # Get API key from session state
            api_key = st.session_state.get("gemini_api_key", "")
            
            if not api_key:
                st.error("❌ Please enter and save your Gemini API key in the sidebar first.")
            else:
                # Progress bar for better UX
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("Initializing planning agents...")
                progress_bar.progress(10)
                
                try:
                    # Run pipeline with API key
                    result = orchestrator.run_pipeline(user_input, api_key=api_key)
                    
                    status_text.text("Finalizing your plan...")
                    progress_bar.progress(100)
                    
                    # Display results
                    if result.get("status") == "success":
                        st.success("✅ Plan generated successfully!")
                        
                        # Main plan display
                        plan = result.get("plan", {})
                        st.markdown(format_plan_display(plan))
                        
                        # Verification
                        verification = result.get("verification", {})
                        if verification:
                            st.markdown(
                                """
                                <div class="custom-card">
                                    <h2>🔍 Plan Verification</h2>
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                            
                            is_valid = verification.get("is_valid", False)
                            status_icon = "✅" if is_valid else "⚠️"
                            
                            col1, col2 = st.columns([1, 4])
                            with col1:
                                st.markdown(f"### {status_icon}")
                            with col2:
                                st.markdown(f"### Plan Status: {'VALID' if is_valid else 'NEEDS REVIEW'}")
                            
                            if verification.get("verification_summary"):
                                with st.expander("📋 Verification Details", expanded=False):
                                    st.text(verification.get("verification_summary"))
                        
                        # Recommendations
                        recommendations = result.get("recommendations", [])
                        if recommendations:
                            st.markdown(
                                """
                                <div class="custom-card">
                                    <h2>💡 Smart Recommendations</h2>
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                            
                            for i, rec in enumerate(recommendations):
                                st.info(f"**{i+1}.** {rec}")
                        
                        # Evaluation metrics
                        evaluation = result.get("evaluation", {})
                        if evaluation:
                            st.markdown(
                                """
                                <div class="custom-card">
                                    <h2>📊 Plan Evaluation</h2>
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                            
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric(
                                    "Overall Score",
                                    f"{evaluation.get('overall_score', 0.0):.2%}",
                                    delta="High" if evaluation.get('overall_score', 0.0) > 0.7 else "Medium"
                                )
                            with col2:
                                st.metric(
                                    "Goal Satisfaction",
                                    f"{evaluation.get('goal_satisfaction_score', 0.0):.2%}",
                                    delta="Optimal" if evaluation.get('goal_satisfaction_score', 0.0) > 0.8 else "Good"
                                )
                            with col3:
                                st.metric(
                                    "Constraint Compliance",
                                    f"{evaluation.get('constraint_compliance', 0.0):.2%}",
                                    delta="High" if evaluation.get('constraint_compliance', 0.0) > 0.8 else "Medium"
                                )
                            with col4:
                                budget_dev = evaluation.get("budget_deviation", 0.0)
                                st.metric(
                                    "Budget Deviation",
                                    f"{budget_dev:.1f}%" if budget_dev > 0 else "0%",
                                    delta="Optimal" if budget_dev == 0 else "Over"
                                )
                        
                        # Execution trace
                        if show_trace:
                            st.markdown(
                                """
                                <div class="custom-card">
                                    <h2>🔗 Execution Trace</h2>
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                            
                            trace = result.get("trace", [])
                            for i, step in enumerate(trace, 1):
                                with st.expander(f"Step {i}: {step.get('agent', 'Unknown')}", expanded=False):
                                    st.json(step.get("result", {}))
                        
                        # Logs
                        if show_logs:
                            st.markdown(
                                """
                                <div class="custom-card">
                                    <h2>📝 Detailed Logs</h2>
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                            
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
                
                except Exception as e:
                    st.error(f"❌ An unexpected error occurred: {str(e)}")
                
                finally:
                    # Clear progress indicators
                    progress_bar.empty()
                    status_text.empty()
    
    # Footer
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style="text-align: center; color: #BB86FC;">
                <h3>Smart Life Planner</h3>
                <p>Multi-agent planning system with ADK architecture, tools, memory, and observability.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )


if __name__ == "__main__":
    main()