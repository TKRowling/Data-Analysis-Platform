import { useState } from 'react';
import { Correlation } from '../../components/eda/Correlation';
import { DataQuality } from '../../components/eda/DataQuality';
import { DatasetOverview } from '../../components/eda/DatasetOverview';
import { Distribution } from '../../components/eda/Distribution';
import { FeatureEngineering } from '../../components/eda/FeatureEngineering';
import { Statistics } from '../../components/eda/Statistics';
import { Empty, ErrorBanner, Loading, Tabs, Title } from '../../components/common';
import { useEDA } from '../../hooks/useEDA';
import { getCorrelation, getOverview, getQuality, getStatistics } from '../../services/edaApi';
import type { Dataset } from '../../types/dataset';

const TABS = ['Overview', 'Statistics', 'Data quality', 'Correlation', 'Distribution', 'Feature engineering'];

export function ExploratoryAnalysisPage({ dataset, revision }: { dataset: Dataset | null; revision: number }) {
  const [tab, setTab] = useState(TABS[0]);
  const [method, setMethod] = useState('pearson');
  const [localRevision, setLocalRevision] = useState(0);
  const version = revision + localRevision;
  const id = dataset?.id;

  // The overview drives the column list every other tab uses.
  const overview = useEDA(id, getOverview, [version]);
  const statistics = useEDA(tab === 'Statistics' ? id : undefined, getStatistics, [version]);
  const quality = useEDA(tab === 'Data quality' ? id : undefined, getQuality, [version]);
  const correlation = useEDA(tab === 'Correlation' ? id : undefined,
                             (datasetId) => getCorrelation(datasetId, method), [method, version]);

  if (!dataset) return <Empty />;
  const columns = overview.data?.columns ?? [];

  return (
    <>
      <Title eyebrow="EXPLORATORY ANALYSIS" title="Understand your dataset"
             text="Profile structure, statistical behaviour, quality, and relationships before making decisions." />
      <Tabs tabs={TABS} active={tab} onSelect={setTab} />

      {tab === 'Overview' && (
        overview.loading ? <Loading /> :
        overview.error ? <ErrorBanner message={overview.error} /> :
        overview.data ? <DatasetOverview data={overview.data} /> : null
      )}

      {tab === 'Statistics' && (
        statistics.loading ? <Loading /> :
        statistics.error ? <ErrorBanner message={statistics.error} /> :
        statistics.data ? <Statistics data={statistics.data} /> : null
      )}

      {tab === 'Data quality' && (
        quality.loading ? <Loading /> :
        quality.error ? <ErrorBanner message={quality.error} /> :
        quality.data ? <DataQuality data={quality.data} /> : null
      )}

      {tab === 'Correlation' && (
        correlation.loading ? <Loading /> :
        correlation.error ? <ErrorBanner message={correlation.error} /> :
        correlation.data ? <Correlation data={correlation.data} method={method} onMethodChange={setMethod} /> : null
      )}

      {tab === 'Distribution' && <Distribution dataset={dataset} columns={columns} revision={version} />}

      {tab === 'Feature engineering' && (
        <FeatureEngineering dataset={dataset} columns={columns}
                            onChanged={() => setLocalRevision((n) => n + 1)} />
      )}
    </>
  );
}
