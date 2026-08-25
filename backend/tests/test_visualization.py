from app.schemas.visualization import ChartRequest
from app.services.visualization_service import create_chart

def test_visualization_returns_plotly_spec(sample_record):
    figure=create_chart(sample_record,ChartRequest(chart_type="bar",x="region",y="revenue",aggregation="sum"))
    assert figure["data"][0]["type"]=="bar"

