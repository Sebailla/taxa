// PR 2c literal deep-import anti-pattern for app-shell/domain.
// ESLint MUST reject this; the path `src/modules/app-shell/domain/deep`
// is a layer-folder import, which spec.md rule 5 forbids.
import { something } from "src/modules/app-shell/domain/deep";
console.log(something);
