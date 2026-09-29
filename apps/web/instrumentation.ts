// Runs once when the Next.js server starts. The import sits inside the runtime check so the
// Edge build leaves the Node-only module out (form from the Next.js docs).
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { installieren } = await import("./lib/api-verbindung");
    installieren();
  }
}
