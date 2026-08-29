// PR 2c literal deep-import anti-pattern for design-system/presentation.
// ESLint MUST reject this; the path `src/modules/design-system/presentation/deep`
// is a layer-folder import, which spec.md rule 5 forbids.
import { something } from "src/modules/design-system/presentation/deep";
console.log(something);
