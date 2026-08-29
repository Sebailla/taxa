// PR 2c literal deep-import anti-pattern for taxonomy/infrastructure.
// ESLint MUST reject this; the path `src/modules/taxonomy/infrastructure/deep`
// is a layer-folder import, which spec.md rule 5 forbids.
import { something } from "src/modules/taxonomy/infrastructure/deep";
console.log(something);
