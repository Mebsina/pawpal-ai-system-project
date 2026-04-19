import streamlit as st
from ai.utils import ReliabilityAuditor

def render_ai_metrics():
    """Renders the system evaluation metrics as a standalone page."""
    st.header("AI Metrics")
    st.write("Monitor the performance and reliability of the PawPal+ AI agents.")
    
    metrics = ReliabilityAuditor.get_metrics_summary()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("AI Reliability Score", f"{int(metrics['score'] * 100)}%")
    with col2:
        st.metric("Avg Confidence", f"{int(metrics['avg_confidence'] * 100)}%")
    with col3:
        st.metric("Total Interactions", metrics['count'])
        
    st.progress(metrics['score'], text="Overall AI Reliability")
    
    st.divider()
    
    st.subheader("Detailed Tool Performance")
    tool_metrics = ReliabilityAuditor.get_per_tool_metrics()
    
    if not tool_metrics:
        st.caption("No interactive data collected yet.")
    else:
        for tm in tool_metrics:
            st.markdown(f"#### {tm['tool']}")
            st.write(f"&emsp;&emsp;**Confidence:** {int(tm['avg_confidence'] * 100)}%")
            
            rel_per = int(tm['reliability'] * 100)
            rel_color = "green" if rel_per >= 80 else "orange" if rel_per >= 50 else "red"
            st.markdown(f"&emsp;&emsp;**Reliability:** :{rel_color}[{rel_per}%]")

    if metrics.get('last_update'):
        st.caption(f"Last system sync: {metrics['last_update'][:16].replace('T', ' ')}")
    
