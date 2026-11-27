import React from 'react';
import clsx from 'clsx';
import styles from './styles.module.css';

const iconProps = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  viewBox: '0 0 24 24',
};

function AppsIcon(props) {
  return (
    <svg {...iconProps} {...props}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}

function ExtendIcon(props) {
  return (
    <svg {...iconProps} {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v8M8 12h8" />
    </svg>
  );
}

function AnsibleIcon(props) {
  return (
    <svg {...iconProps} {...props}>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="m7 9 3 3-3 3M12.5 15H17" />
    </svg>
  );
}

const FeatureList = [
  {
    title: 'Over Fifty Applications',
    Icon: AppsIcon,
    description: (
      <>Easily install over fifty different applications onto your home server.</>
    ),
  },
  {
    title: 'Easily Extensible',
    Icon: ExtendIcon,
    description: (
      <>Simple to extend with more applications by adding a new Ansible role.</>
    ),
  },
  {
    title: 'Powered by Ansible',
    Icon: AnsibleIcon,
    description: <>Built from scratch with Ansible.</>,
  },
];

function Feature({Icon, title, description}) {
  return (
    <div className={clsx('col col--4')}>
      <div className={styles.featureCard}>
        <div className={styles.iconBadge}>
          <Icon className={styles.featureIcon} role="img" aria-label={title} />
        </div>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
