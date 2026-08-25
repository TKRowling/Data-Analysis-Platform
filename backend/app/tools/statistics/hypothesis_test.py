from scipy import stats

def independent_t_test(left, right) -> dict:
    result = stats.ttest_ind(left, right, nan_policy="omit", equal_var=False)
    return {"statistic": float(result.statistic), "p_value": float(result.pvalue)}

