import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Config
API_URL = "http://localhost:8000/api"

st.set_page_config(page_title="Analytics Dashboard", page_icon="📊", layout="wide")

st.title("📊 Analytics Dashboard")
st.caption("Monitor chatbot performance and usage")

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    days = st.slider("Time Period (days)", 1, 90, 7)
    
    if st.button("🔄 Refresh Data"):
        st.rerun()

# Fetch dashboard data
try:
    response = requests.get(f"{API_URL}/analytics/dashboard?days={days}")
    if response.status_code == 200:
        data = response.json()
        
        usage_stats = data.get("usage_stats", {})
        performance = data.get("performance_metrics", {})
        errors = data.get("recent_errors", [])
        
        # === USAGE STATISTICS ===
        st.header("📈 Usage Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Queries",
                f"{usage_stats.get('total_queries', 0):,}",
                help="Total number of queries in selected period"
            )
        
        with col2:
            st.metric(
                "Unique Sessions",
                f"{usage_stats.get('unique_sessions', 0):,}",
                help="Number of unique user sessions"
            )
        
        with col3:
            st.metric(
                "Avg Response Time",
                f"{usage_stats.get('avg_response_time_ms', 0):.0f}ms",
                help="Average response time"
            )
        
        with col4:
            cache_rate = usage_stats.get('cache_hit_rate', 0) * 100
            st.metric(
                "Cache Hit Rate",
                f"{cache_rate:.1f}%",
                help="Percentage of queries served from cache"
            )
        
        # === FEEDBACK SUMMARY ===
        st.header("💬 User Feedback")
        
        feedback = usage_stats.get('feedback_summary', {})
        thumbs_up = feedback.get('thumbs_up', 0)
        thumbs_down = feedback.get('thumbs_down', 0)
        satisfaction = feedback.get('satisfaction_rate', 0) * 100
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("👍 Thumbs Up", thumbs_up)
        
        with col2:
            st.metric("👎 Thumbs Down", thumbs_down)
        
        with col3:
            st.metric("Satisfaction Rate", f"{satisfaction:.1f}%")
        
        # Feedback chart
        if thumbs_up > 0 or thumbs_down > 0:
            fig = go.Figure(data=[go.Pie(
                labels=['Thumbs Up', 'Thumbs Down'],
                values=[thumbs_up, thumbs_down],
                marker=dict(colors=['#28a745', '#dc3545']),
                hole=0.4
            )])
            fig.update_layout(
                title="Feedback Distribution",
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # === PERFORMANCE METRICS ===
        st.header("⚡ Performance Metrics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Avg Embedding Time",
                f"{performance.get('avg_embedding_time_ms', 0):.0f}ms"
            )
        
        with col2:
            st.metric(
                "Avg Search Time",
                f"{performance.get('avg_search_time_ms', 0):.0f}ms"
            )
        
        with col3:
            st.metric(
                "Avg LLM Time",
                f"{performance.get('avg_llm_time_ms', 0):.0f}ms"
            )
        
        # Performance breakdown
        perf_data = {
            'Component': ['Embedding', 'Search', 'LLM'],
            'Time (ms)': [
                performance.get('avg_embedding_time_ms', 0),
                performance.get('avg_search_time_ms', 0),
                performance.get('avg_llm_time_ms', 0)
            ]
        }
        
        fig = px.bar(
            perf_data,
            x='Component',
            y='Time (ms)',
            title='Performance Breakdown',
            color='Component',
            color_discrete_sequence=['#17a2b8', '#ffc107', '#dc3545']
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Response time percentiles
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("P50 Response Time", f"{performance.get('p50_response_time_ms', 0):.0f}ms")
        
        with col2:
            st.metric("P95 Response Time", f"{performance.get('p95_response_time_ms', 0):.0f}ms")
        
        with col3:
            st.metric("P99 Response Time", f"{performance.get('p99_response_time_ms', 0):.0f}ms")
        
        # === ERROR LOGS ===
        st.header("🚨 Recent Errors")
        
        if errors:
            error_df = pd.DataFrame(errors)
            error_df['created_at'] = pd.to_datetime(error_df['created_at'])
            
            # Display errors table
            st.dataframe(
                error_df[['error_type', 'error_message', 'severity', 'endpoint', 'created_at']],
                use_container_width=True,
                hide_index=True
            )
            
            # Error severity distribution
            severity_counts = error_df['severity'].value_counts()
            fig = px.pie(
                values=severity_counts.values,
                names=severity_counts.index,
                title='Error Severity Distribution'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("✓ No errors in the selected period!")
        
        # === UPLOADS ===
        st.header("📤 Upload Statistics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Uploads", usage_stats.get('total_uploads', 0))
        
        # === EXPORT DATA ===
        st.header("💾 Export Data")
        
        if st.button("📥 Export Stats to CSV"):
            # Create CSV data
            export_data = {
                "Metric": [
                    "Total Queries",
                    "Unique Sessions",
                    "Avg Response Time (ms)",
                    "Cache Hit Rate",
                    "Thumbs Up",
                    "Thumbs Down",
                    "Satisfaction Rate",
                    "Total Uploads"
                ],
                "Value": [
                    usage_stats.get('total_queries', 0),
                    usage_stats.get('unique_sessions', 0),
                    usage_stats.get('avg_response_time_ms', 0),
                    usage_stats.get('cache_hit_rate', 0),
                    thumbs_up,
                    thumbs_down,
                    satisfaction,
                    usage_stats.get('total_uploads', 0)
                ]
            }
            
            df = pd.DataFrame(export_data)
            csv = df.to_csv(index=False)
            
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    else:
        st.error(f"Error fetching analytics: {response.status_code}")
        st.code(response.text)

except Exception as e:
    st.error(f"Failed to connect to analytics API: {str(e)}")
    st.info("Make sure the FastAPI server is running on http://localhost:8000")
