export type Health = { status: "ok"; service: "web" };

export function healthBody(): Health {
  return { status: "ok", service: "web" };
}
