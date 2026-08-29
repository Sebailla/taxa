// PR 2b canonical deep-import anti-pattern. ESLint MUST reject this —
// the path `src/modules/taxonomy/domain/taxon` is a layer-folder import.
import { something } from "src/modules/taxonomy/domain/taxon";
console.log(something);
