// PR 2b allowed-barrel fixture. ESLint MUST allow this — the path
// `src/modules/taxonomy` resolves to the public barrel.
import { something } from "src/modules/taxonomy";
console.log(something);
