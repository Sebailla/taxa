// PR 2c literal deep-import anti-pattern for browser-state/application.
// ESLint MUST reject this; the path `src/modules/browser-state/application/deep`
// is a layer-folder import, which spec.md rule 5 forbids.
import { something } from "src/modules/browser-state/application/deep";
console.log(something);
