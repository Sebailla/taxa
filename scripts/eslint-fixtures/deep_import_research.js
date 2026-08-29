// PR 2b deep-import anti-pattern for the `research` capability. Exercises
// a non-`taxonomy` capability so the rule's coverage of every
// capability's layer folders is asserted at runtime.
import { something } from "src/modules/research/application/useThing";
console.log(something);
