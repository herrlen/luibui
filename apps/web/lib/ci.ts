// The GitHub Actions workflow shown in the developer area (S5-5). The token never appears in
// it: it goes into the repository secret LUIBUI_TOKEN.
export const ACTION = "herrlen/luibui/action@v1";

export function ciWorkflow(projektId: string, pfad = "."): string {
  return `name: luibui
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
  security-events: write
jobs:
  pruefen:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - id: luibui
        uses: ${ACTION}
        with:
          token: \${{ secrets.LUIBUI_TOKEN }}
          projekt: ${projektId}
          pfad: ${pfad}
          schwelle: rot
      - if: always() && steps.luibui.outputs.sarif != ''
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: \${{ steps.luibui.outputs.sarif }}
          category: luibui
`;
}
