import { Bot, Activity } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

const NAV = [
  { to: "/",          label: "Dashboard" },
  { to: "/agents",    label: "Agents" },
  { to: "/workflows", label: "Workflows" },
  { to: "/monitor",   label: "Monitor" },
];

export function Header() {
  const { pathname } = useLocation();

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-slate-200 h-14 flex items-center px-6 gap-6 shadow-sm">
      {/* Logo */}
      <Link to="/" className="flex items-center gap-2 text-brand-600 font-bold text-lg shrink-0">
        <Bot size={22} />
        <span>YUNO AI</span>
      </Link>

      {/* Nav */}
      <nav className="flex items-center gap-1 flex-1">
        {NAV.map(n => (
          <Link
            key={n.to}
            to={n.to}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition
              ${pathname === n.to
                ? "bg-brand-50 text-brand-600"
                : "text-slate-600 hover:bg-slate-100"}`}
          >
            {n.label}
          </Link>
        ))}
      </nav>

      {/* Right */}
      <a
        href="http://localhost:8000/docs"
        target="_blank"
        rel="noreferrer"
        className="flex items-center gap-1 text-xs text-slate-500 hover:text-brand-600 transition"
      >
        <Activity size={14} />
        API Docs
      </a>
    </header>
  );
}
