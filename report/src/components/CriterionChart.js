import React from 'react';
import gradesData from '@site/data/grades.json';

const TOOL_LABELS = {
  pypsa: 'PyPSA',
  powermodels: 'PowerModels.jl',
  powersimulations: 'PowerSimulations.jl',
  gridcal: 'GridCal',
  pandapower: 'pandapower',
  matpower: 'MATPOWER',
};

export default function CriterionChart({ criterion }) {
  const grades = gradesData.tools.map((tool) => {
    const entry = gradesData.grades.find(
      (g) => g.tool === tool && g.criterion === criterion
    );
    return { tool, ...entry };
  });

  return (
    <div className="criterion-chart">
      {grades.map(({ tool, tier, numeric }) => (
        <div
          key={tool}
          className={`criterion-chart__row${tool === 'matpower' ? ' reference-row' : ''}`}
        >
          <span className="criterion-chart__label">{TOOL_LABELS[tool] || tool}</span>
          <div className="criterion-chart__track">
            <div
              className={`criterion-chart__bar tier-${tier.toLowerCase()}`}
              style={{ width: `${(numeric / 3) * 100}%` }}
            >
              {tier}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
