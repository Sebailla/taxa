// PR 2c literal deep-import anti-pattern for browser-state/presentation.
// ESLint MUST reject this; the path `src/modules/browser-state/presentation/deep`
// is a layer-folder import, which spec.md rule 5 forbids.
import { something } from "src/modules/browser-state/presentation/deep";
console.log(something);
