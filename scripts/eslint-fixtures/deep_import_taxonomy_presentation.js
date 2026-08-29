// PR 2c literal deep-import anti-pattern for taxonomy/presentation.
// ESLint MUST reject this; the path `src/modules/taxonomy/presentation/deep`
// is a layer-folder import, which spec.md rule 5 forbids.
import { something } from "src/modules/taxonomy/presentation/deep";
console.log(something);
