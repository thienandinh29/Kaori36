import Link from "next/link";
import {
  BookOpen,
  ClipboardCheck,
  House,
  PenLine,
  Route,
  type LucideIcon,
} from "lucide-react";
import { vi } from "@/messages/vi";
import { Sena } from "@/components/sena/sena";

const t = vi.english;
const LINKS = [
  { href: "/", label: t.nav.today },
  { href: "/lo-trinh", label: t.nav.roadmap },
  { href: "/ban-do", label: t.nav.maps },
  { href: "/tu-vung", label: t.homeToday.vocabTitle },
  { href: "/viet", label: t.nav.writing },
  { href: "/doc", label: t.nav.reading },
  { href: "/nghe", label: t.nav.listening },
  { href: "/phat-am", label: t.nav.pronunciation },
  { href: "/kiem-tra", label: t.nav.levelTest },
  { href: "/gioi-thieu", label: t.about.nav },
  { href: "/kham-pha", label: t.nav.explore },
] as const;
type Href = (typeof LINKS)[number]["href"];

// The phone tab bar: the five places a learner goes every day (specs/ui-v2).
const TABS: { href: Href; label: string; icon: LucideIcon }[] = [
  { href: "/", label: t.tabs.today, icon: House },
  { href: "/lo-trinh", label: t.tabs.roadmap, icon: Route },
  { href: "/tu-vung", label: t.tabs.vocab, icon: BookOpen },
  { href: "/viet", label: t.tabs.writing, icon: PenLine },
  { href: "/kiem-tra", label: t.tabs.test, icon: ClipboardCheck },
];

export function EnglishShell({
  active,
  wide = false,
  children,
}: {
  /** The nav entry to mark; none for pages outside the nav (the owner's tools). */
  active?: Href;
  /** Full-width pages (the roadmap); others keep a reading column. */
  wide?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="en-shell">
      <header className="en-header">
        <Link href="/" className="en-brand">
          <span className="en-brand-face" aria-hidden="true">
            <Sena pose="idle" label={vi.sena} />
          </span>
          <span>
            <strong>{vi.app}</strong>
            <small>{t.brandSub}</small>
          </span>
        </Link>
        <nav className="en-nav" aria-label={vi.app}>
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={link.href === active ? "page" : undefined}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <Link className="en-about-link" href="/gioi-thieu">
          {t.about.nav}
        </Link>
      </header>
      <main className={wide ? "en-main is-wide" : "en-main"}>{children}</main>
      <nav className="en-tabbar" aria-label={t.tabs.label}>
        {TABS.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            aria-current={href === active ? "page" : undefined}
          >
            <Icon aria-hidden="true" size={22} strokeWidth={2} />
            {label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
