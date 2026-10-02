import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { QrCode } from "./Sicherheit";

describe("QrCode", () => {
  it("draws one square per dark module inside a quiet zone", () => {
    const html = renderToStaticMarkup(<QrCode zeilen={["101", "010", "111"]} />);
    expect(html).toContain('viewBox="0 0 11 11"');
    // one white background plus six dark modules
    expect(html.match(/<rect /g)).toHaveLength(7);
    expect(html).toContain('x="4" y="4"');
    expect(html).not.toContain('x="5" y="4"');
    expect(html).toContain('aria-label="QR-Code für die Authenticator-App"');
  });
});
