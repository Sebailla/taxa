// Presentation-layer barrel for the design-system module (PR 5b.4
// promotion of the TabStrip primitive).
//
// Cross-module consumers MUST import only from this file (or via the
// `@taxa/design-system` public barrel). Deep imports into this folder
// are blocked by `.eslintrc.cjs::no-restricted-imports`.

export {
  TabStrip,
  type TabDefinition,
  type TabStripProps,
} from "./TabStrip";
