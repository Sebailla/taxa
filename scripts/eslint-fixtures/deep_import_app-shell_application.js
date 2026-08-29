// PR 2c literal deep-import anti-pattern for app-shell/application.
// ESLint MUST reject this; the path `src/modules/app-shell/application/deep`
// is a layer-folder import, which spec.md rule 5 forbids.
import { something } from "src/modules/app-shell/application/deep";
console.log(something);
