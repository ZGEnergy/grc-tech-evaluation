// @ts-check
/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Phase 1 Technology Evaluation',
  tagline: 'Power-system modeling tool evaluation for ZGEnergy',
  favicon: 'img/favicon.ico',

  url: 'https://zge-energy.github.io',
  baseUrl: '/grc-tech-evaluation/',

  organizationName: 'zge-energy',
  projectName: 'grc-tech-evaluation',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  customFields: {
    protocolVersion: 'v7',
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          routeBasePath: '/',
          sidebarPath: './sidebars.js',
          showLastUpdateTime: true,
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      navbar: {
        title: 'Phase 1 Evaluation',
        items: [
          {
            href: 'https://github.com/zge-energy/grc-tech-evaluation',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        copyright: `Protocol version: v7 | Built with Docusaurus`,
      },
    }),
};

module.exports = config;
