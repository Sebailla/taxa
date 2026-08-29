// PR 2c literal deep-import anti-pattern for taxonomy/application.
// ESLint MUST reject this; the path `src/modules/taxonomy/application/deep`
// is a layer-folder import, which spec.md rule 5 forbids.
import { something } from "src/modules/taxonomy/application/deep";
console.log(something);
