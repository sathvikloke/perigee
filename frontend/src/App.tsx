import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createHttpApi, type PerigeeApi } from "./api/client";
import type { FrameRecord, PresetDescriptor } from "./api/types";
import { Home } from "./components/Home";
import { PresetInvestigation } from "./components/PresetInvestigation";
import { QueryInvestigation } from "./components/QueryInvestigation";
import { createFixtureApi } from "./fixtures/devFixture";
import { parseRoute, routeToSearch, type Route } from "./lib/route";

function initialFixtureMode(): boolean {
  const p = new URLSearchParams(window.location.search);
  if (p.has("fixtures")) return p.get("fixtures") === "1";
  return import.meta.env.VITE_USE_FIXTURES === "1";
}

export function App() {
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.search));
  const [fixtureMode, setFixtureMode] = useState(initialFixtureMode);
  const api: PerigeeApi = useMemo(() => (fixtureMode ? createFixtureApi() : createHttpApi()), [fixtureMode]);
  // Frames already processed this session, keyed by data source + frame_key.
  const frameCache = useRef(new Map<string, FrameRecord>());

  useEffect(() => {
    const onPop = () => {
      setRoute(parseRoute(window.location.search));
      setFixtureMode(initialFixtureMode());
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const navigate = useCallback(
    (next: Route, replace = false) => {
      const url = `${window.location.pathname}${routeToSearch(next, fixtureMode)}`;
      if (replace) window.history.replaceState(null, "", url);
      else window.history.pushState(null, "", url);
      setRoute(next);
      if (!replace) window.scrollTo(0, 0);
    },
    [fixtureMode],
  );

  const setFixtures = (on: boolean) => {
    const p = new URLSearchParams(window.location.search);
    if (on) p.set("fixtures", "1");
    else p.delete("fixtures");
    const s = p.toString();
    window.history.replaceState(null, "", `${window.location.pathname}${s ? `?${s}` : ""}`);
    setFixtureMode(on);
  };
  const useFixture = () => setFixtures(true);

  // Move focus to the new view's heading so keyboard and screen reader users land in context.
  const mainRef = useRef<HTMLElement>(null);
  const routeKey = route.view === "preset" ? `preset:${route.presetId}` : route.view;
  useEffect(() => {
    const h1 = mainRef.current?.querySelector("h1");
    if (h1) {
      h1.setAttribute("tabindex", "-1");
      h1.focus({ preventScroll: true });
    }
  }, [routeKey]);

  // "My evidence": the notebook on an investigation, or the saved list on the home view.
  const goToEvidence = (e: React.MouseEvent) => {
    e.preventDefault();
    const target = document.getElementById("notebook") ?? document.getElementById("my-evidence");
    if (target) {
      target.scrollIntoView();
      return;
    }
    navigate({ view: "home" });
    window.setTimeout(() => document.getElementById("my-evidence")?.scrollIntoView(), 50);
  };

  const openQueryAt = (preset: PresetDescriptor) =>
    navigate({
      view: "query",
      ra: String(preset.query_center?.ra_deg ?? ""),
      dec: String(preset.query_center?.dec_deg ?? ""),
      fov: String(preset.default_fov_arcmin ?? 6),
      caseId: preset.case_ids[0],
    });

  return (
    <>
      <a className="skip" href="#main">
        Skip to investigation
      </a>
      {fixtureMode && (
        <div className="fixture-banner" role="note">
          <strong>Development fixture — not NASA data.</strong> Images are placeholders; nothing comes from the API.{" "}
          <button type="button" className="link" onClick={() => setFixtures(false)}>
            Switch to the live API
          </button>
        </div>
      )}
      <header className="topbar">
        <a
          href={`${window.location.pathname}${fixtureMode ? "?fixtures=1" : ""}`}
          className="brand"
          aria-label="Perigee home"
          onClick={(e) => {
            e.preventDefault();
            navigate({ view: "home" });
          }}
        >
          <svg viewBox="0 0 36 36" aria-hidden="true">
            <circle cx="18" cy="18" r="10" />
            <ellipse cx="18" cy="18" rx="17" ry="6" transform="rotate(-36 18 18)" />
            <circle className="satellite" cx="29" cy="9" r="3" />
          </svg>
          perigee
          <span className="brand-divider" aria-hidden="true" />
          <span className="brand-caption">
            A closer look at
            <br />
            our infrared sky
          </span>
        </a>
        <nav aria-label="Main">
          <ul>
            <li>
              <a
                href="?"
                className="wide-only"
                aria-current={route.view !== "query" ? "page" : undefined}
                onClick={(e) => {
                  e.preventDefault();
                  navigate({ view: "home" });
                }}
              >
                Investigations
              </a>
            </li>
            <li>
              <a
                href="?view=query"
                aria-current={route.view === "query" ? "page" : undefined}
                onClick={(e) => {
                  e.preventDefault();
                  navigate({ view: "query" });
                }}
              >
                {/* One text node per breakpoint: an inline span with a leading space
                    produced "Search  coordinates" in the accessible name. */}
                <span className="wide-only">Search coordinates</span>
                <span className="phone-only">Search</span>
              </a>
            </li>
            <li>
              <a href="#my-evidence" onClick={goToEvidence}>
                My evidence
              </a>
            </li>
          </ul>
        </nav>
      </header>

      <main id="main" ref={mainRef} tabIndex={-1}>
        {route.view === "home" && (
          <Home
            api={api}
            onOpenPreset={(id) => navigate({ view: "preset", presetId: id })}
            onOpenQuery={() => navigate({ view: "query" })}
            onUseFixture={useFixture}
          />
        )}
        {route.view === "preset" && (
          <PresetInvestigation
            key={`${api.mode}:${route.presetId}`}
            api={api}
            presetId={route.presetId}
            onUseFixture={useFixture}
            onQueryPosition={openQueryAt}
            onOpenPreset={(id) => navigate({ view: "preset", presetId: id })}
            onOpenQuery={() => navigate({ view: "query" })}
          />
        )}
        {route.view === "query" && (
          <QueryInvestigation
            key={`${api.mode}:query`}
            api={api}
            initial={route}
            frameCache={frameCache.current}
            onUseFixture={useFixture}
            onQueryChange={(q) =>
              navigate(
                {
                  view: "query",
                  ra: String(q.ra_deg),
                  dec: String(q.dec_deg),
                  fov: String(q.fov_arcmin),
                  caseId: route.caseId,
                },
                true,
              )
            }
          />
        )}
      </main>

      <footer className="site-footer">
        <span>
          PERIGEE <span className="footer-dot">·</span> Explore what the evidence supports{" "}
          <span className="footer-dot">·</span> v{__APP_VERSION__} · {fixtureMode ? "development fixture" : "live API"}
          {!fixtureMode && import.meta.env.DEV && (
            <>
              {" · "}
              <button type="button" className="link" onClick={useFixture}>
                Use development fixture
              </button>
            </>
          )}
        </span>
        <a href="https://irsa.ipac.caltech.edu/Missions/spherex.html" target="_blank" rel="noreferrer">
          Explore the SPHEREx archive ↗
        </a>
      </footer>
    </>
  );
}
