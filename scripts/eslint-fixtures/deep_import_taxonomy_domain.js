// PR 2c literal deep-import anti-pattern for taxonomy/domain.
// ESLint MUST reject this; the path `src/modules/taxonomy/domain/deep`
// is a layer-folder import, which spec.md rule 5 forbids.
import { something } from "src/modules/taxonomy/domain/deep";
console.log(something);
