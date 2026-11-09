const fs = require('fs');
const path = require('path');

const APPLICATIONS_DIR = 'applications';

function readCategoryLabels(siteDir) {
  const applicationsDir = path.join(siteDir, 'docs', APPLICATIONS_DIR);
  const labels = {};
  for (const entry of fs.readdirSync(applicationsDir, {withFileTypes: true})) {
    if (!entry.isDirectory()) {
      continue;
    }
    try {
      const config = JSON.parse(
        fs.readFileSync(
          path.join(applicationsDir, entry.name, '_category_.json'),
          'utf8',
        ),
      );
      labels[entry.name] = config.label;
    } catch {
      // A folder without a readable category config falls back to its name.
    }
  }
  return labels;
}

function categoryFromId(id) {
  const [, category] = id.split('/');
  return category.split('-').join(' ');
}

module.exports = function applicationsIndexPlugin(context) {
  return {
    name: 'applications-index',
    async contentLoaded({allContent, actions}) {
      const docsContent = allContent['docusaurus-plugin-content-docs']?.default;
      const version =
        docsContent?.loadedVersions.find((candidate) => candidate.isLast) ??
        docsContent?.loadedVersions[0];
      const labels = readCategoryLabels(context.siteDir);

      const applications = (version?.docs ?? [])
        .filter(
          (doc) =>
            doc.id.startsWith(`${APPLICATIONS_DIR}/`) &&
            !doc.draft &&
            !doc.unlisted,
        )
        .map((doc) => ({
          id: doc.id,
          title: doc.title,
          // Docusaurus derives a description from the first paragraph, which for
          // these pages is usually the upstream link; only show authored ones.
          description: doc.frontMatter?.description ?? '',
          // Matching still uses the derived text so keywords in the intro count.
          searchText: `${doc.title} ${doc.id} ${doc.description ?? ''}`,
          permalink: doc.permalink,
          category:
            labels[doc.sourceDirName.split('/')[1]] ?? categoryFromId(doc.id),
        }))
        .sort((a, b) => a.title.localeCompare(b.title));

      actions.setGlobalData({applications});
    },
  };
};
