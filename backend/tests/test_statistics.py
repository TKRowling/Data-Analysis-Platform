from app.tools.statistics.aggregation import aggregate

def test_grouped_aggregation(sample_record):
    result=aggregate(sample_record.frame,"revenue","sum","region")
    assert result.loc[result.region=="North","revenue"].iloc[0]==250

