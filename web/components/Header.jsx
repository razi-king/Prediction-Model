"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/** Top bar shared by every page: logo, navigation, API / Cassandra status dots. */
export default function Header() {
  const pathname = usePathname();
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(false));
  }, []);

  return (
    <header className="header">
      <div className="brand">
        <div className="brand-mark" aria-hidden>▲</div>
        <div>
          <h1>DevAscend</h1>
          <p>Developer growth predictor · trained on 153k developers from the Stack Overflow Survey</p>
        </div>
      </div>
      <nav className="nav">
        <Link href="/" className={pathname === "/" ? "active" : ""}>Predictor</Link>
        <Link href="/accuracy" className={pathname === "/accuracy" ? "active" : ""}>Model accuracy</Link>
      </nav>
      <div className="header-status">
        <span><span className={`dot ${health ? "on" : "off"}`} />API</span>
        <span><span className={`dot ${health?.cassandra ? "on" : "off"}`} />Cassandra</span>
      </div>
    </header>
  );
}
