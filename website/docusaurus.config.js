// @ts-check
// Note: type annotations allow type checking and IDEs autocompletion

const lightCodeTheme = require('prism-react-renderer').themes.github;
const darkCodeTheme = require('prism-react-renderer').themes.dracula;

const baseUrl = '/ansible-nas/';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Ansible-NAS',
  tagline: 'Easily build a homelab or NAS replacement with an Ubuntu server and some basic hardware',
  url: 'https://hitluca.github.io',
  baseUrl,
  onBrokenLinks: 'throw',
  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },
  favicon: 'img/favicon.ico',

  headTags: [
    {
      tagName: 'link',
      attributes: {rel: 'icon', type: 'image/png', href: `${baseUrl}img/favicon.png`},
    },
    {
      tagName: 'link',
      attributes: {rel: 'apple-touch-icon', href: `${baseUrl}img/apple-touch-icon.png`},
    },
  ],

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'HitLuca', // Usually your GitHub org/user name.
  projectName: 'ansible-nas', // Usually your repo name.
  trailingSlash: true,

  // Even if you don't use internalization, you can use this field to set useful
  // metadata like html lang. For example, if your site is Chinese, you may want
  // to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  plugins: [
    require.resolve('./plugins/applications-index'),
    require.resolve('./plugins/changelog'),
  ],

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          // Please change this to your repo.
          // Remove this to remove the "edit this page" links.
          editUrl:
            'https://github.com/HitLuca/ansible-nas/tree/main/website',
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {
        defaultMode: 'light',
        respectPrefersColorScheme: true,
      },
      navbar: {
        title: 'Ansible-NAS',
        logo: {
          src: 'img/logo.png',
          alt: 'Ansible-NAS',
        },
        items: [
          {
            type: 'doc',
            docId: 'index',
            position: 'left',
            label: 'Docs',
          },
          {
            type: 'doc',
            docId: '/category/getting-started',
            position: 'left',
            label: 'Getting Started',
          },
          {
            type: 'doc',
            docId: '/category/applications',
            position: 'left',
            label: 'Applications',
          },
          {to: '/changelog', label: 'Changelog', position: 'left'},
          {
            href: 'https://github.com/HitLuca/ansible-nas',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Docs',
            items: [
              {
                label: 'Getting Started',
                to: 'docs/category/getting-started',
              },
              {
                label: 'Support',
                to: 'docs/support',
              },
            ],
          },
          {
            title: 'More',
            items: [
              {
                label: 'GitHub',
                href: 'https://github.com/HitLuca/ansible-nas',
              },
            ],
          },
        ],
        copyright: `Copyright © 2017-${new Date().getFullYear()} David Stephens, © ${new Date().getFullYear()} Luca Simonetto. Site built with Docusaurus.`,
      },
      image: 'img/logo.png',
      prism: {
        theme: lightCodeTheme,
        darkTheme: darkCodeTheme,
      },
    }),
};

module.exports = config;
