# README images: source

`showcase.html` holds every README picture except the two viewer screenshots: one dark page,
inline SVG, no scripts. Open it in a browser to see all of it. `render.js` screenshots its
sections into `docs/images/`:

```bash
NODE_PATH=<a node_modules folder with playwright> node docs/images/src/render.js
```

It needs the `playwright` package, Google Chrome and `cwebp` (libwebp); every image is saved as
lossless WebP. Change the text or the SVG in `showcase.html`, then render again.

`viewer.webp` and `demo-task.webp` are screenshots of the viewer (`sae view`) on a copy of a demo
task: `viewer.webp` on a trimmed copy, `demo-task.webp` on the whole task. Convert a new
screenshot with `cwebp -lossless -z 9 shot.png -o <name>.webp`.
