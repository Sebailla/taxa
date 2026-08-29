// PR 2c literal deep-import anti-pattern for browser-state/infrastructure.
// ESLint MUST reject this; the path `src/modules/browser-state/infrastructure/deep`
// is a layer-folder import, which spec.md rule 5 forbids.
import { something } from "src/modules/browser-state/infrastructure/deep";
console.log(something);
