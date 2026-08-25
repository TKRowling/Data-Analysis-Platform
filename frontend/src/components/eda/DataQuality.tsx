import { Card, DataTable, Metric } from '../common';
import { humanize } from '../../utils/formatters';
import type { Quality } from '../../types/eda';

function verdict(score: number): string {
  if (score >= 90) return 'Excellent — this dataset is analysis-ready.';
  if (score >= 70) return 'Good foundation with a few issues to review.';
  return 'Review these data issues before relying on downstream analysis.';
}

export function DataQuality({ data }: { data: Quality }) {
  const withOutliers = data.outliers.filter((o) => o.count > 0);
  return (
    <>
      <div className="score">
        <div>
          <small>DATA QUALITY SCORE</small>
          <b>{data.score}</b>
          <span>/ 100</span>
        </div>
        <p>{verdict(data.score)}</p>
      </div>

      <div className="metrics">
        <Metric label="DUPLICATE ROWS" value={data.duplicate_rows} note={`${data.duplicate_percent}% of rows`} />
        <Metric label="COLUMNS WITH GAPS" value={data.missing.length} />
        <Metric label="FIELDS WITH OUTLIERS" value={withOutliers.length} />
        <Metric label="DATATYPE ISSUES" value={data.datatype_issues.length} />
      </div>

      <Card title="Missing values" sub="Columns containing at least one gap">
        <DataTable rows={data.missing as unknown as Record<string, unknown>[]} empty="No missing values anywhere in this dataset." />
      </Card>

      <Card title="Duplicate row analysis" sub="Rows identical across every column">
        {data.duplicate_rows > 0
          ? <p className="insight">{data.duplicate_rows.toLocaleString()} duplicate rows ({data.duplicate_percent}% of the dataset). They are counted, not removed — decide whether they are genuine repeat records before dropping them.</p>
          : <p className="muted-text">No duplicate rows detected.</p>}
      </Card>

      <Card title="Outlier detection (IQR method)" sub="Values beyond 1.5 × IQR from the quartiles. Detected only; nothing is removed.">
        <DataTable rows={withOutliers as unknown as Record<string, unknown>[]} empty="No IQR outliers detected in any numeric column." />
      </Card>

      <Card title="Datatype consistency" sub="Columns whose stored type disagrees with their contents">
        {data.datatype_issues.length ? (
          <ul className="issue-list">
            {data.datatype_issues.map((issue, index) => (
              <li key={`${issue.column}-${index}`} className={`issue ${issue.severity}`}>
                <span className="issue-tag">{issue.severity}</span>
                <div>
                  <b>{issue.column}</b> <em>({issue.dtype})</em> — {humanize(issue.issue)}
                  <p>{issue.detail}</p>
                </div>
              </li>
            ))}
          </ul>
        ) : <p className="muted-text">Every column's stored type matches its contents.</p>}
      </Card>
    </>
  );
}
