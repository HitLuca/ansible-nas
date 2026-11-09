import React, {useMemo} from 'react';
import {
  PageMetadata,
  useCurrentSidebarCategory,
} from '@docusaurus/theme-common';
import useBaseUrl from '@docusaurus/useBaseUrl';
import DocCardList from '@theme/DocCardList';
import DocPaginator from '@theme/DocPaginator';
import DocVersionBanner from '@theme/DocVersionBanner';
import DocVersionBadge from '@theme/DocVersionBadge';
import DocBreadcrumbs from '@theme/DocBreadcrumbs';
import Heading from '@theme/Heading';
import {
  ApplicationSearchBox,
  useApplicationSearch,
} from '@site/src/components/ApplicationSearch';
import styles from './styles.module.css';

function collectDocIds(items, ids = []) {
  for (const item of items) {
    if (item.type === 'doc') {
      ids.push(item.id);
    } else if (item.type === 'category') {
      collectDocIds(item.items, ids);
    } else if (item.type === 'link' && item.docId) {
      ids.push(item.docId);
    }
  }
  return ids;
}
function DocCategoryGeneratedIndexPageMetadata({categoryGeneratedIndex}) {
  return (
    <PageMetadata
      title={categoryGeneratedIndex.title}
      description={categoryGeneratedIndex.description}
      keywords={categoryGeneratedIndex.keywords}
      // TODO `require` this?
      image={useBaseUrl(categoryGeneratedIndex.image)}
    />
  );
}
function DocCategoryGeneratedIndexPageContent({categoryGeneratedIndex}) {
  const category = useCurrentSidebarCategory();
  const docIds = useMemo(
    () => collectDocIds(category.items),
    [category.items],
  );
  const search = useApplicationSearch({docIds});
  const isSearching = search.trimmedQuery !== '';
  return (
    <div className={styles.generatedIndexPage}>
      <DocVersionBanner />
      <DocBreadcrumbs />
      <DocVersionBadge />
      <header>
        <Heading as="h1" className={styles.title}>
          {categoryGeneratedIndex.title}
        </Heading>
        {categoryGeneratedIndex.description && (
          <p>{categoryGeneratedIndex.description}</p>
        )}
      </header>
      {search.total > 0 && (
        <div className={styles.categorySearch}>
          <ApplicationSearchBox
            search={search}
            id="category-application-search"
          />
        </div>
      )}
      {!isSearching && (
        <article className="margin-top--lg">
          <DocCardList items={category.items} className={styles.list} />
        </article>
      )}
      <footer className="margin-top--lg">
        <DocPaginator
          previous={categoryGeneratedIndex.navigation.previous}
          next={categoryGeneratedIndex.navigation.next}
        />
      </footer>
    </div>
  );
}
export default function DocCategoryGeneratedIndexPage(props) {
  return (
    <>
      <DocCategoryGeneratedIndexPageMetadata {...props} />
      <DocCategoryGeneratedIndexPageContent {...props} />
    </>
  );
}
