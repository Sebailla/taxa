// PR 2c literal deep-import anti-pattern for research/domain.
// ESLint MUST reject this; the path `src/modules/research/domain/deep`
// is a layer-folder import, which spec.md rule 5 forbids.
import { something } from "src/modules/research/domain/deep";
console.log(something);
