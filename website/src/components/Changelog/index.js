import React from 'react';
import clsx from 'clsx';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import {usePluginData} from '@docusaurus/useGlobalData';

import styles from './styles.module.css';

// Changelog entries only use `code` and [text](url).
function Inline({text}) {
  return text.split(/(`[^`]+`|\[[^\]]+\]\([^)]+\))/).map((part, i) => {
    const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (link) return <a key={i} href={link[2]}>{link[1]}</a>;
    if (part.startsWith('`')) return <code key={i}>{part.slice(1, -1)}</code>;
    return part;
  });
}

function formatDate(date) {
  return new Date(`${date}T00:00:00Z`).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

function Release({release, apps, latest}) {
  const breaking = release.sections.find((s) => s.title === 'Breaking');
  const major = Boolean(breaking?.items.length);
  const dated = /^\d{4}-\d{2}-\d{2}$/.test(release.date);
  return (
    <article className={styles.release} id={release.version}>
      <div className={styles.rail}>
        <span className={clsx(styles.dot, latest && styles.dotLatest)} />
      </div>
      <div className={styles.card}>
        <header className={styles.header}>
          <h2 className={styles.version}>{release.version}</h2>
          {latest && <span className={clsx(styles.badge, styles.latest)}>Latest</span>}
          {major && <span className={clsx(styles.badge, styles.major)}>Major</span>}
          {dated && <time className={styles.date}>{formatDate(release.date)}</time>}
        </header>
        {release.intro.map((p, i) => (
          <p key={i}><Inline text={p} /></p>
        ))}
        {release.added.length > 0 && (
          <section>
            <h3 className={styles.heading}>New applications</h3>
            <ul className={styles.chips}>
              {release.added.map((name) => {
                const app = apps.find((a) => a.title.toLowerCase() === name.toLowerCase());
                return (
                  <li key={name}>
                    {app ? <Link to={app.permalink}>{name}</Link> : <span>{name}</span>}
                  </li>
                );
              })}
            </ul>
          </section>
        )}
        {release.sections.map((section) => (
          <section
            key={section.title}
            className={section.title === 'Breaking' ? styles.breaking : undefined}>
            <h3 className={styles.heading}>
              {section.title === 'Breaking' ? '⚠ Breaking changes' : section.title}
            </h3>
            <ul>
              {section.items.map((item, i) => (
                <li key={i}><Inline text={item} /></li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </article>
  );
}

export default function Changelog({releases}) {
  const {applications} = usePluginData('applications-index') ?? {applications: []};
  const unreleased = releases.find((r) => r.version === 'Unreleased');
  const pending = unreleased && (unreleased.sections.length || unreleased.added.length);
  const shown = releases.filter((r) => r.version !== 'Unreleased' || pending);
  const latest = releases.find((r) => r.version !== 'Unreleased')?.version;
  return (
    <Layout title="Changelog" description="What changed between Ansible-NAS releases">
      <header className={clsx('hero hero--primary', styles.hero)}>
        <div className="container">
          <h1 className="hero__title">Changelog</h1>
          <p className="hero__subtitle">What changed between releases</p>
        </div>
      </header>
      <main className={clsx('container', styles.main)}>
        <p className={styles.lede}>
          Breaking changes and new applications. A new <strong>major</strong> version means
          read this page before upgrading. Image bumps and bug fixes are in the{' '}
          <Link href="https://github.com/HitLuca/ansible-nas/releases">GitHub release notes</Link>.
        </p>
        <div className={styles.timeline}>
          {shown.map((r) => (
            <Release key={r.version} release={r} apps={applications} latest={r.version === latest} />
          ))}
        </div>
      </main>
    </Layout>
  );
}
