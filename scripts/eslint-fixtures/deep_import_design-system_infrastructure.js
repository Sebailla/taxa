// PR 2c literal deep-import anti-pattern for design-system/infrastructure.
// ESLint MUST reject this; the path `src/modules/design-system/infrastructure/deep`
// is a layer-folder import, which spec.md rule 5 forbids.
import { something } from "src/modules/design-system/infrastructure/deep";
console.log(something);
