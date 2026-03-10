import React from 'react';
import gradesData from '@site/data/grades.json';

/**
 * Map a letter grade (e.g. "A-", "B+", "C") to its CSS class name.
 */
export function letterToClassName(letter) {
  if (!letter) return '';
  const base = letter.charAt(0).toLowerCase();
  const modifier = letter.length > 1 ? letter.charAt(1) : '';

  if (modifier === '+') return `grade-${base}-plus`;
  if (modifier === '-') return `grade-${base}-minus`;
  return `grade-${base}`;
}

/**
 * Capitalize a criterion slug for display (e.g. "supply_chain" -> "Supply Chain").
 */
function formatCriterion(slug) {
  return slug
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Look up the grade entry for a given tool + criterion.
 */
function findGrade(tool, criterion) {
  return gradesData.grades.find((g) => g.tool === tool && g.criterion === criterion);
}

/**
 * Compute the weighted average numeric grade for a tool across the given criteria.
 */
function computeAverage(tool, criteriaList) {
  const entries = criteriaList
    .map((c) => findGrade(tool, c))
    .filter(Boolean);
  if (entries.length === 0) return null;
  const sum = entries.reduce((acc, e) => acc + e.numeric, 0);
  return sum / entries.length;
}

// Tools that are reference-only (not primary candidates)
const REFERENCE_TOOLS = new Set(['matpower', 'powersimulations']);

/**
 * GradeTable — renders a comparison table of tool grades across rubric criteria.
 *
 * Props:
 *   showRank       — show a numeric rank column (default: true)
 *   includeReference — include reference-only tools like matpower (default: true)
 *   criteria       — array of criterion slugs to display; defaults to all
 *   className      — additional CSS class for the wrapper table
 */
export default function GradeTable({
  showRank = true,
  includeReference = true,
  criteria,
  className,
}) {
  const criteriaList = criteria || gradesData.criteria;
  const allTools = gradesData.tools;

  // Filter tools based on includeReference
  const tools = includeReference
    ? allTools
    : allTools.filter((t) => !REFERENCE_TOOLS.has(t));

  // Compute averages and sort by descending average for ranking
  const toolAverages = tools.map((tool) => ({
    tool,
    average: computeAverage(tool, criteriaList),
    isReference: REFERENCE_TOOLS.has(tool),
  }));
  toolAverages.sort((a, b) => (b.average || 0) - (a.average || 0));

  const tableClass = ['grade-table', className].filter(Boolean).join(' ');

  return (
    <table className={tableClass}>
      <thead>
        <tr>
          {showRank && <th>#</th>}
          <th>Tool</th>
          {criteriaList.map((c) => (
            <th key={c}>{formatCriterion(c)}</th>
          ))}
          <th>Avg</th>
        </tr>
      </thead>
      <tbody>
        {toolAverages.map((entry, idx) => {
          const rowClass = entry.isReference ? 'reference-row' : undefined;
          return (
            <tr key={entry.tool} className={rowClass}>
              {showRank && <td>{idx + 1}</td>}
              <td>{entry.tool}</td>
              {criteriaList.map((c) => {
                const grade = findGrade(entry.tool, c);
                if (!grade) return <td key={c}>—</td>;
                return (
                  <td key={c}>
                    <span className={letterToClassName(grade.letter)}>
                      {grade.letter}
                    </span>
                  </td>
                );
              })}
              <td>{entry.average != null ? entry.average.toFixed(1) : '—'}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
