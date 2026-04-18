import streamlit as st
from ai.utils import ReliabilityAuditor

def render_sidebar():
    """Renders the system evaluation metrics in the sidebar."""
    with st.sidebar:
        st.subheader("System Evaluation")
        metrics = ReliabilityAuditor.get_metrics_summary()
        st.metric("AI Reliability Score", f"{int(metrics['score'] * 100)}%")
        st.caption(f"Based on {metrics['count']} interactions")
        st.progress(metrics['score'])
        
        with st.expander("Detailed Metrics"):
            st.write("### System Overall")
            st.write(f"**Ave Confidence Score:** {int(metrics['avg_confidence'] * 100)}%")
            st.write(f"**Total interactions:** {metrics['count']}")
            
            st.divider()
            st.write("### Per-Action Performance")
            tool_metrics = ReliabilityAuditor.get_per_tool_metrics()
            
            if not tool_metrics:
                st.caption("No interactive data collected yet.")
            
            for tm in tool_metrics:
                st.markdown(f"**{tm['tool']}**")
                st.write(f"Confidence score: {int(tm['avg_confidence'] * 100)}%")
                
                # Use color-coding for reliability percentage
                rel_per = int(tm['reliability'] * 100)
                rel_color = "green" if rel_per >= 80 else "orange" if rel_per >= 50 else "red"
                st.markdown(f"Reliability: :{rel_color}[{rel_per}%]")
                st.write("---")

            if metrics.get('last_update'):
                st.caption(f"Last update: {metrics['last_update'][:16].replace('T', ' ')}")
        
        st.divider()
        st.caption("PawPal+ Reliability Auditor v1.0")
