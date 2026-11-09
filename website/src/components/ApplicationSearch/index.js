import React, {useMemo, useState} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import {useHistory} from '@docusaurus/router';
import {usePluginData} from '@docusaurus/useGlobalData';
import styles from './styles.module.css';

const MAX_RESULTS = 8;

function haystackFor(application) {
  return `${application.searchText} ${application.category}`.toLowerCase();
}

function rank(application, terms) {
  const title = application.title.toLowerCase();
  if (terms.every((term) => title.startsWith(term))) {
    return 0;
  }
  if (terms.every((term) => title.includes(term))) {
    return 1;
  }
  return 2;
}

/**
 * State and matching for the application search. `docIds` scopes the results to
 * a subset of the index, used by the generated category pages.
 */
export function useApplicationSearch({docIds} = {}) {
  const {applications = []} = usePluginData('applications-index') ?? {};
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const history = useHistory();

  const candidates = useMemo(() => {
    if (!docIds) {
      return applications;
    }
    const allowed = new Set(docIds);
    return applications.filter((application) => allowed.has(application.id));
  }, [applications, docIds]);

  const trimmedQuery = query.trim().toLowerCase();
  const results = useMemo(() => {
    if (trimmedQuery === '') {
      return [];
    }
    const terms = trimmedQuery.split(/\s+/);
    return candidates
      .filter((application) =>
        terms.every((term) => haystackFor(application).includes(term)),
      )
      .sort(
        (a, b) =>
          rank(a, terms) - rank(b, terms) || a.title.localeCompare(b.title),
      )
      .slice(0, MAX_RESULTS);
  }, [candidates, trimmedQuery]);

  function handleChange(event) {
    setQuery(event.target.value);
    setActiveIndex(0);
  }

  function handleKeyDown(event) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((current) => Math.min(current + 1, results.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((current) => Math.max(current - 1, 0));
    } else if (event.key === 'Enter') {
      const selected = results[activeIndex];
      if (selected) {
        event.preventDefault();
        history.push(selected.permalink);
      }
    } else if (event.key === 'Escape') {
      setQuery('');
    }
  }

  return {
    total: candidates.length,
    query,
    setQuery,
    trimmedQuery,
    results,
    activeIndex,
    setActiveIndex,
    handleChange,
    handleKeyDown,
  };
}

export function ApplicationSearchBox({
  search,
  label = 'Find an application',
  id = 'application-search',
}) {
  const {
    total,
    query,
    trimmedQuery,
    results,
    activeIndex,
    setActiveIndex,
    handleChange,
    handleKeyDown,
  } = search;
  const resultsId = `${id}-results`;
  const hintId = `${id}-hint`;

  return (
    <>
      <label className={styles.label} htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        className={styles.input}
        type="search"
        placeholder="Search applications by name or description..."
        autoComplete="off"
        value={query}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        aria-describedby={hintId}
        role="combobox"
        aria-expanded={trimmedQuery !== ''}
        aria-controls={resultsId}
        aria-activedescendant={
          results[activeIndex] ? `${resultsId}-${activeIndex}` : undefined
        }
      />
      <p id={hintId} className={styles.hint}>
        {trimmedQuery === ''
          ? `Search ${total} applications by name or description.`
          : `${results.length} matching application${
              results.length === 1 ? '' : 's'
            }.`}
      </p>
      {trimmedQuery !== '' && (
        <ul id={resultsId} className={styles.results} role="listbox">
          {results.length === 0 && (
            <li className={styles.empty}>
              No applications match &ldquo;{query.trim()}&rdquo;.
            </li>
          )}
          {results.map((application, index) => (
            <li
              key={application.permalink}
              id={`${resultsId}-${index}`}
              role="option"
              aria-selected={index === activeIndex}>
              <Link
                to={application.permalink}
                className={clsx(
                  styles.result,
                  index === activeIndex && styles.active,
                )}
                onMouseEnter={() => setActiveIndex(index)}>
                <span className={styles.resultTitle}>{application.title}</span>
                <span className={styles.resultCategory}>
                  {application.category}
                </span>
                {application.description && (
                  <span className={styles.resultDescription}>
                    {application.description}
                  </span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export default function ApplicationSearch() {
  const search = useApplicationSearch();
  return (
    <section className={styles.search}>
      <div className="container">
        <div className={styles.searchBox}>
          <ApplicationSearchBox search={search} />
        </div>
      </div>
    </section>
  );
}
