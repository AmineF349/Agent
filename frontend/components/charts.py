import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List, Dict, Any

def price_timeseries_chart(prices: List[float], timestamps: List[str] = None, title: str = "Prix Day-Ahead"):
    if timestamps:
        x = timestamps[:len(prices)]
    else:
        x = list(range(len(prices)))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=prices, mode='lines', name='Prix', line=dict(color='#003366')))
    fig.update_layout(
        title=title,
        xaxis_title="Temps",
        yaxis_title="EUR/MWh",
        template="plotly_white",
        height=400
    )
    return fig

def price_histogram(prices: List[float], title: str = "Distribution Prix"):
    fig = px.histogram(x=prices, nbins=50, title=title, color_discrete_sequence=['#0099CC'])
    fig.update_layout(xaxis_title="EUR/MWh", yaxis_title="Fréquence", template="plotly_white", height=400)
    return fig

def capture_rate_gauge(capture_rate: float, technology: str = "solar"):
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=capture_rate,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"Capture Rate {technology}"},
        delta={'reference': 0.8},
        gauge={
            'axis': {'range': [None, 1.2]},
            'bar': {'color': "#003366"},
            'steps': [
                {'range': [0, 0.7], 'color': "#FFCCCC"},
                {'range': [0.7, 0.9], 'color': "#FFFFCC"},
                {'range': [0.9, 1.2], 'color': "#CCFFCC"}
            ],
            'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 0.7}
        }
    ))
    fig.update_layout(height=300)
    return fig

def scenario_comparison_chart(afry_price: float, aurora_price: float, internal_price: float = None):
    categories = ['AFRY', 'Aurora']
    values = [afry_price, aurora_price]
    if internal_price:
        categories.append('Interne')
        values.append(internal_price)
    fig = go.Figure([go.Bar(x=categories, y=values, marker_color=['#003366', '#0099CC', '#FF6600'][:len(categories)])])
    fig.update_layout(title="Comparaison Baseload 2030", yaxis_title="EUR/MWh", template="plotly_white", height=400)
    return fig

def kpi_cards(metrics: Dict[str, Any]):
    # Returns dict for display, actual rendering in Streamlit
    return metrics
