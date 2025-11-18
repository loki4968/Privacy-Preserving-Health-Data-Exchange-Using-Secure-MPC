'use client';

import React from 'react';
import StatsMetricsChart from './StatsMetricsChart';
import OrgDistributionChart from './OrgDistributionChart';
import ThresholdChart from './ThresholdChart';
import RiskLevelChart from './RiskLevelChart';

function SecureAnalysisChartsSection({ result }) {
  return (
    <section className="space-y-4">
      <div>
        <h3 className="text-xl font-semibold text-gray-900">Core Visual Metrics</h3>
        <p className="text-sm text-gray-500">
          High-level cohort patterns rendered with privacy-preserving aggregated
          metrics.
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <StatsMetricsChart result={result} />
        <OrgDistributionChart result={result} />
        <ThresholdChart result={result} />
        <RiskLevelChart result={result} />
      </div>
    </section>
  );
}

export default SecureAnalysisChartsSection;
