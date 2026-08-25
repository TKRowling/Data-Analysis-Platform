from app.schemas.visualization import ChartRequest
from app.services.visualization_service import create_chart

def test_visualization_returns_plotly_spec(sample_record):
    figure=create_chart(sample_record,ChartRequest(chart_type="bar",x="region",y="revenue",aggregation="sum"))
    assert figure["data"][0]["type"]=="bar"

def test_line_chart_accepts_multiple_y_columns(sample_record):
    request=ChartRequest(chart_type="line",x="region",y_columns=["revenue","units"],aggregation="none")
    figure=create_chart(sample_record,request)
    assert len(figure["data"])==2

def test_heatmap_accepts_selected_columns(sample_record):
    request=ChartRequest(chart_type="heatmap",columns=["revenue","units"])
    figure=create_chart(sample_record,request)
    assert figure["data"][0]["type"]=="heatmap"
    assert list(figure["data"][0]["x"])==["revenue","units"]
