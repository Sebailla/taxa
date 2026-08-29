// PR 2c literal deep-import anti-pattern for research/application.
// ESLint MUST reject this; the path `src/modules/research/application/deep`
// is a layer-folder import, which spec.md rule 5 forbids.
import { something } from "src/modules/research/application/deep";
console.log(something);
