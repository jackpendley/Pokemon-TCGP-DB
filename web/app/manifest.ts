import type { MetadataRoute } from "next";

/**
 * Web app manifest — makes the site installable to a phone home screen and
 * launchable without browser chrome, which is the honest answer to "should this
 * be a native app": everything it needs is a URL and a responsive layout.
 *
 * `theme_color` is the app's primary red (--primary, oklch(0.57 0.21 27)),
 * matching the generated icons in public/.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "TCGP Collection Optimizer",
    short_name: "TCGP",
    description:
      "Pokémon TCG Pocket collection progress and EV-based pack recommendations",
    start_url: "/",
    display: "standalone",
    background_color: "#0d1117",
    theme_color: "#d72828",
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
    ],
  };
}
