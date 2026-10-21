// Renders the README images in docs/images/ from showcase.html, one section or element each.
// Run from anywhere: NODE_PATH=<a node_modules folder with playwright> node docs/images/src/render.js
// Uses the installed Google Chrome and cwebp (libwebp): every image is saved as lossless WebP.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { chromium } = require('playwright');

const SOURCE = path.join(__dirname, 'showcase.html');
const OUT_DIR = path.join(__dirname, '..');

// The hero image: the title block alone, centered, as wide as the rows. Applied after tree.webp.
const HERO_CSS = `
#hero .ht,#hero .meta{display:none}
#hero .w{max-width:1240px;grid-template-columns:minmax(0,1fr);justify-items:center}
#hero .hl{width:100%;text-align:center}
#hero .k{justify-content:center}
#hero h1{max-width:none}
#hero .hl>svg.d{width:780px;margin:48px auto 0}`;

// [file, element, margin around it in px, extra CSS applied first]
const IMAGES = [
  ['tree.webp', '#hero .ht', 32],
  ['hero.webp', '#hero', 0, HERO_CSS],
  ['why.webp', '#why'],
  ['row-1.webp', '#row-1'],
  ['row-2.webp', '#row-2'],
  ['row-3.webp', '#row-3'],
  ['row-4.webp', '#row-4'],
  ['row-5.webp', '#row-5'],
  ['row-6.webp', '#row-6'],
  ['row-7.webp', '#row-7'],
  ['pipeline.webp', '#pipeline'],
  ['prose.webp', '#prose'],
];

// The README has its own headings and links: hide the page's, and the full-screen section height.
const README_CSS = `
section{min-height:0 !important;border-top:0 !important}
#hero .meta,#why .sh,#pipeline .sh,#prose .sh,#prose .lead{display:none}
.pipe .d,.prose .d{margin-top:0 !important}`;

(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  // 1320 px is above the page's 1000 px breakpoint: every row keeps problem and fix side by side.
  const page = await browser.newPage({ viewport: { width: 1320, height: 900 }, deviceScaleFactor: 2, colorScheme: 'dark' });
  await page.goto('file://' + SOURCE, { waitUntil: 'load' });
  await page.addStyleTag({ content: README_CSS });
  for (const [file, selector, margin = 0, css] of IMAGES) {
    if (css) await page.addStyleTag({ content: css });
    const box = await page.locator(selector).boundingBox();
    const clip = { x: box.x - margin, y: box.y - margin, width: box.width + 2 * margin, height: box.height + 2 * margin };
    const png = path.join(os.tmpdir(), file.replace(/\.webp$/, '.png'));
    await page.screenshot({ path: png, clip, fullPage: true });
    execFileSync('cwebp', ['-quiet', '-lossless', '-z', '9', png, '-o', path.join(OUT_DIR, file)]);
    fs.unlinkSync(png);
    console.log(file);
  }
  await browser.close();
})();
