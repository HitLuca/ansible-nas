const fs = require('fs');
const path = require('path');

// CHANGELOG.md at the repo root stays the single source; this turns it into
// structured data for the /changelog page at build time.
function parse(text) {
  const releases = [];
  for (const chunk of text.split(/^## /m).slice(1)) {
    const [heading, ...rest] = chunk.split('\n');
    const [version, date = ''] = heading.split(/\s+—\s+/);
    const release = {
      version: version.trim(),
      date: date.trim(),
      intro: [],
      added: [],
      sections: [],
    };
    let current = null;
    for (const line of rest.join('\n').split('\n')) {
      const h3 = line.match(/^### (.+)/);
      const added = line.match(/^Added applications:\s*(.+?)\.?$/);
      if (h3) {
        current = {title: h3[1].trim(), items: []};
        release.sections.push(current);
      } else if (added && !current) {
        release.added = added[1].split(',').map((name) => name.trim());
      } else if (current && line.startsWith('- ')) {
        current.items.push(line.slice(2).trim());
      } else if (!current && line.trim() && line.trim() !== 'Nothing yet.') {
        release.intro.push(line.trim());
      }
    }
    releases.push(release);
  }
  return releases;
}

module.exports = function changelogPlugin(context) {
  const file = path.join(context.siteDir, '..', 'CHANGELOG.md');
  return {
    name: 'changelog',
    getPathsToWatch: () => [file],
    async contentLoaded({actions}) {
      const releases = parse(fs.readFileSync(file, 'utf8'));
      const data = await actions.createData(
        'changelog.json',
        JSON.stringify(releases),
      );
      actions.addRoute({
        path: `${context.baseUrl}changelog`,
        exact: true,
        component: '@site/src/components/Changelog',
        modules: {releases: data},
      });
    },
  };
};
