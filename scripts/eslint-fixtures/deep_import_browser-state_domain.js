// PR 2c literal deep-import anti-pattern for browser-state/domain.
// ESLint MUST reject this; the path `src/modules/browser-state/domain/deep`
// is a layer-folder import, which spec.md rule 5 forbids.
import { something } from "src/modules/browser-state/domain/deep";
console.log(something);
