/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  reportSidebar: [
    'index',
    'grid-primer',
    'use-cases-criteria',
    'tools-evaluated',
    {
      type: 'category',
      label: 'Evaluation Results',
      collapsed: false,
      items: [
        'results/index',
        'results/expressiveness',
        'results/extensibility',
        'results/scalability',
        'results/accessibility',
        'results/maturity',
        'results/supply-chain',
        'results/head-to-head',
        'results/sweep-findings',
        'results/probe-results',
      ],
    },
  ],
};

module.exports = sidebars;
