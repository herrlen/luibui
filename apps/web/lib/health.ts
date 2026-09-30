export type Health = { status: "ok"; service: "web"; version: string };

/** ``version``: the image tag baked in at build time (scripts/release.sh), "lokal" otherwise. */
export function healthBody(): Health {
  return { status: "ok", service: "web", version: process.env.LUIBUI_VERSION || "lokal" };
}
