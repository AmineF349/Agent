import streamlit as st

def metric_card(label: str, value: str, delta: str = None, help_text: str = None):
    st.metric(label=label, value=value, delta=delta, help=help_text)

def insight_card(text: str, type: str = "info"):
    if type == "warning":
        st.warning(text)
    elif type == "error":
        st.error(text)
    elif type == "success":
        st.success(text)
    else:
        st.info(text)

def kpi_row(metrics: dict):
    cols = st.columns(4)
    with cols[0]:
        st.metric("Baseload", f"{metrics.get('baseload', 0)} €/MWh")
    with cols[1]:
        st.metric("Peakload", f"{metrics.get('peakload', 0)} €/MWh")
    with cols[2]:
        st.metric("Negative Hours", f"{metrics.get('negative_hours', 0)} ({metrics.get('negative_hours_pct',0)}%)")
    with cols[3]:
        cr = metrics.get('capture_rate')
        if cr:
            st.metric("Capture Rate", f"{cr}", delta=f"{(cr-0.8)*100:.0f}% vs 0.8 ref")
        else:
            st.metric("Volatility", f"{metrics.get('volatility',0)}")
