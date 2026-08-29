// PR 2c literal deep-import anti-pattern for research/infrastructure.
// ESLint MUST reject this; the path `src/modules/research/infrastructure/deep`
// is a layer-folder import, which spec.md rule 5 forbids.
import { something } from "src/modules/research/infrastructure/deep";
console.log(something);
