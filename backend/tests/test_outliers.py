from app.tools.quality.outliers import iqr_outliers

def test_iqr_outlier_detection(sample_record):
    assert iqr_outliers(sample_record.frame["revenue"])["count"]==1

