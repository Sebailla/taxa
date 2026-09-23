"use client";

/**
 * AppShellNav — the four-destination navigation header that
 * ships as part of the ODD-ASN-002 product navigation surface.
 *
 * Client island: depends on `usePathname()` from `next/navigation`
 * to resolve the current route so the active destination carries
 * `aria-current="page"` + the primary-tint + bottom-border
 * affordance the design system prescribes.
 *
 * spec.md rule 4 / rule 5: this component depends only on the
 * `next/navigation` hook + the design-system tokens in
 * `globals.css`. No HTTP, no browser-state, no framework
 * dependencies beyond React + the App Router navigation surface.
 */
import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavLink {
  readonly href: string;
  readonly label: string;
}

/**
 * The four top-level destinations the brief requires. Order is
 * pinned: Classification / Browser / Help / Settings (the brief
 * explicitly lists these four in this exact order so the
 * navigation surface is consistent across every route).
 */
const NAV_LINKS: readonly NavLink[] = [
  { href: "/", label: "Classification" },
  { href: "/explorer", label: "Browser" },
  { href: "/help", label: "Help" },
  { href: "/settings", label: "Settings" },
];

/** Return true iff `pathname` matches `href`. The home route
 *  (`/`) requires an exact match so the index does not stay
 *  marked-active while the user browses `/explorer` etc. */
const isActive = (pathname: string, href: string): boolean => {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
};

export interface AppShellNavProps {
  /** Optional override for the navigation destinations (test
   *  harnesses + future slices can inject a different
   *  link list). Defaults to the four-destination brief. */
  readonly links?: readonly NavLink[];
}

export default function AppShellNav(
  props: AppShellNavProps,
): React.ReactElement {
  const pathname = usePathname();
  const links = props.links ?? NAV_LINKS;
  return (
    <nav
      className="app-shell-nav flex items-center gap-1"
      aria-label="Primary"
      data-app-shell-nav=""
      data-app-shell-nav-count={links.length}
    >
      {links.map((link) => {
        const active = isActive(pathname, link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            className={
              active
                ? "app-shell-nav-link app-shell-nav-link--active"
                : "app-shell-nav-link"
            }
            data-app-shell-nav-link=""
            data-app-shell-nav-href={link.href}
            aria-current={active ? "page" : undefined}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}