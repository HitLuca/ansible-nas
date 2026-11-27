import React from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import useBaseUrl from '@docusaurus/useBaseUrl';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';
import ApplicationSearch from '@site/src/components/ApplicationSearch';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  const logoUrl = useBaseUrl('img/logo.png');
  return (
    <header className={clsx('hero', styles.heroBanner)}>
      <div className="container">
        <img className={styles.heroLogo} src={logoUrl} alt="" />
        <h1 className="hero__title">{siteConfig.title}</h1>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className="button button--primary button--lg"
            to="docs/getting-started/installation">
            Get started
          </Link>
          <Link
            className="button button--secondary button--lg"
            to="docs/category/applications">
            Browse applications
          </Link>
        </div>
        <div className={styles.heroSearch}>
          <ApplicationSearch />
        </div>
      </div>
    </header>
  );
}

export default function Home() {
  return (
    <Layout
      title="Easy home server setup"
      description="Ansible-NAS turns a stock Ubuntu server into a NAS and homelab: fifty-plus self-hosted applications deployed as Docker containers from a single Ansible playbook.">
      <HomepageHeader />
      <main>
        <HomepageFeatures />
      </main>
    </Layout>
  );
}
