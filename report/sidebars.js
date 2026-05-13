/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  reportSidebar: [
    'index',
    'use-cases-criteria',
    'tools-evaluated',
    'contract-traceability',
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
      ],
    },
  ],
};

module.exports = sidebars;
