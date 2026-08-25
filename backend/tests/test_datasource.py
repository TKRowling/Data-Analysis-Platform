from app.services.dataset_service import load_upload

def test_csv_datasource_loads():
    record=load_upload("tiny.csv",b"name,value\na,1\nb,2\n")
    assert record.frame.shape==(2,2)

