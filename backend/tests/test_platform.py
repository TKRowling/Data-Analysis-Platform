import io
import pandas as pd
from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

def upload_sample():
    frame=pd.DataFrame({"region":["North","South","North","West",None],"revenue":[100,200,150,500,50],"age":[20,30,25,80,22]})
    response=client.post("/api/datasets/upload",files={"file":("sample.csv",frame.to_csv(index=False).encode(),"text/csv")})
    assert response.status_code==201
    return response.json()["id"]

def test_upload_and_eda():
    dataset_id=upload_sample()
    overview=client.get(f"/api/datasets/{dataset_id}/eda/overview")
    assert overview.json()["rows"]==5
    quality=client.get(f"/api/datasets/{dataset_id}/eda/quality")
    assert quality.status_code==200 and quality.json()["score"] <= 100

def test_ai_uses_computed_result():
    dataset_id=upload_sample()
    response=client.post(f"/api/datasets/{dataset_id}/ai-analysis",json={"question":"average revenue by region"})
    assert response.status_code==200
    assert response.json()["verified"] is True

def test_safe_feature_expression():
    dataset_id=upload_sample()
    response=client.post(f"/api/datasets/{dataset_id}/features",json={"name":"revenue_per_age","expression":"revenue / age"})
    assert response.status_code==201
    rejected=client.post(f"/api/datasets/{dataset_id}/features",json={"name":"bad","expression":"__import__('os')"})
    assert rejected.status_code==422

