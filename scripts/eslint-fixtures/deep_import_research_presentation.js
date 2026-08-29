// PR 2c literal deep-import anti-pattern for research/presentation.
// ESLint MUST reject this; the path `src/modules/research/presentation/deep`
// is a layer-folder import, which spec.md rule 5 forbids.
import { something } from "src/modules/research/presentation/deep";
console.log(something);
