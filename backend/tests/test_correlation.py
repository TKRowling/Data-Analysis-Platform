from app.tools.correlation.correlation import correlation_matrix

def test_correlation_matrix_is_square(sample_record):
    result=correlation_matrix(sample_record.frame)
    assert result.shape==(2,2)

