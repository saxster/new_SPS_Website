// REGISTER WIDGET: Risk Calculator
CMS.registerEditorComponent({
  id: "risk_calculator",
  label: "🧮 Risk Calculator",
  fields: [
    { name: "title", label: "Title", widget: "string", default: "Assess Your Facility Risk" },
    { name: "sector", label: "Default Sector", widget: "select", options: ["general", "jewellery", "corporate", "industrial"], default: "general" }
  ],
  pattern: /^{{< risk-calculator title="(.*)" sector="(.*)" >}}$/,
  fromBlock: function(match) {
    return {
      title: match[1],
      sector: match[2]
    };
  },
  toBlock: function(obj) {
    return `{{< risk-calculator title="${obj.title}" sector="${obj.sector}" >}}`;
  },
  toPreview: function(obj) {
    return `
      <div style="padding: 2rem; border: 1px solid #333; background: #111; color: white; font-family: monospace; text-align: center;">
        <h3 style="margin: 0 0 1rem 0; text-transform: uppercase;">${obj.title}</h3>
        <p style="color: #00ff41;">// LIVE RISK CALCULATOR WIDGET</p>
        <p style="font-size: 0.8rem; color: #888;">PRESET: ${obj.sector.toUpperCase()}</p>
        <button style="margin-top: 1rem; padding: 0.5rem 1rem; background: #00ff41; color: black; border: none; font-weight: bold;">START ASSESSMENT</button>
      </div>
    `;
  }
});

// REGISTER PREVIEW: Page Builder (Hero, Features, etc.)
const PagePreview = createClass({
  render: function() {
    const entry = this.props.entry;
    const title = entry.getIn(['data', 'title']);
    const sections = entry.getIn(['data', 'sections']);

    // Helper to render sections
    const renderSection = (section, index) => {
      const type = section.get('type');
      
      if (type === 'hero') {
        const bg = section.get('image');
        return h('div', { key: index, style: { position: 'relative', height: '500px', display: 'flex', alignItems: 'center', borderBottom: '1px solid #333', overflow: 'hidden', backgroundColor: '#000' } },
          bg ? h('img', { src: this.props.getAsset(bg).toString(), style: { position: 'absolute', width: '100%', height: '100%', objectFit: 'cover', opacity: 0.4, filter: 'grayscale(100%)' } }) : null,
          h('div', { style: { position: 'relative', zIndex: 10, padding: '0 5rem', maxWidth: '800px' } },
            h('h2', { style: { fontSize: '4rem', fontWeight: '900', lineHeight: 0.9, marginBottom: '1.5rem', color: '#fff', textTransform: 'uppercase' } }, section.get('title')),
            h('p', { style: { fontSize: '1.2rem', color: '#ccc', borderLeft: '4px solid #00ff41', paddingLeft: '1.5rem' } }, section.get('subtitle'))
          )
        );
      }

      if (type === 'features') {
        const items = section.get('items');
        return h('div', { key: index, style: { padding: '5rem', backgroundColor: '#050505' } },
          section.get('title') ? h('h3', { style: { fontSize: '0.8rem', fontWeight: 'bold', color: '#666', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '3rem' } }, section.get('title')) : null,
          h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '2rem' } },
            items ? items.map((item, i) => h('div', { key: i, style: { padding: '2rem', border: '1px solid #333', backgroundColor: '#111' } },
              h('div', { style: { fontSize: '2rem', marginBottom: '1.5rem', color: '#00ff41' } }, item.get('icon') === 'shield' ? '🛡️' : '⚡'),
              h('h4', { style: { fontSize: '1.2rem', fontWeight: 'bold', marginBottom: '1rem', color: '#fff' } }, item.get('title')),
              h('p', { style: { fontSize: '0.9rem', color: '#888', lineHeight: 1.6 } }, item.get('text'))
            )) : null
          )
        );
      }

      if (type === 'smart_feed') {
        return h('div', { key: index, style: { padding: '4rem 5rem', borderTop: '1px solid #333', borderBottom: '1px solid #333', backgroundColor: '#0a0a0a' } },
          h('h3', { style: { fontSize: '2rem', fontWeight: 'bold', color: '#fff', textTransform: 'uppercase' } }, section.get('title')),
          h('p', { style: { fontSize: '0.8rem', fontFamily: 'monospace', color: '#00ff41' } }, `// LIVE FEED: ${section.get('sector').toUpperCase()}`)
        );
      }

      return h('div', { key: index, style: { padding: '2rem', color: 'red' } }, `Unknown Block: ${type}`);
    };

    return h('div', { style: { fontFamily: 'sans-serif', backgroundColor: '#000', minHeight: '100vh', color: '#fff' } },
      // Header
      h('div', { style: { padding: '2rem 5rem', borderBottom: '1px solid #333' } },
        h('h1', { style: { fontSize: '2.5rem', fontWeight: 'bold', margin: 0 } }, title)
      ),
      // Blocks
      sections ? sections.map(renderSection) : null
    );
  }
});

CMS.registerPreviewTemplate("pages", PagePreview);

// REGISTER AI COMMAND BUTTON
// This adds a button to the markdown toolbar (if supported) or we hook into the event system
// Since standard toolbar extensions are tricky in Decap 2.0, we use a custom Widget wrapper
// or simpler: A global button in the UI.

// Implementation Strategy:
// We will intercept the 'preSave' event to offer an AI check.
CMS.registerEventListener({
  name: 'preSave',
  handler: ({ entry, author }) => {
    const body = entry.getIn(['data', 'body']);
    if (!body || body.length < 50) return; // Skip empty/short

    // In a real implementation, we would fetch() the Python API here.
    // Since we can't easily block for an async fetch in preSave without UI complexity,
    // we will just log it for now or rely on a custom widget button.
    console.log("Saving content...", body.substring(0, 20));
  },
});
