import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createHttpApi, type PerigeeApi } from "./api/client";
import type { FrameRecord, PresetDescriptor } from "./api/types";
import { Home } from "./components/Home";
import { PresetInvestigation } from "./components/PresetInvestigation";
import { QueryInvestigation } from "./components/QueryInvestigation";
import { BrandMark } from "./components/BrandMark";
import { createFixtureApi } from "./fixtures/devFixture";
import { focusHeadingIn } from "./lib/headingFocus";
import { parseRoute, routeToSearch, type Route } from "./lib/route";

/** AI-use disclosure required by the Space Apps submission guide. */
const AI_USE_URL = "https://github.com/sathvikloke/perigee/blob/main/docs/AI_USE.md";

function initialFixtureMode(): boolean {
  const p = new URLSearchParams(window.location.search);
  if (p.has("fixtures")) return p.get("fixtures") === "1";
  return import.meta.env.VITE_USE_FIXTURES === "1";
}

export function App() {
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.search));
  const [fixtureMode, setFixtureMode] = useState(initialFixtureMode);
  const [queryNavigation, setQueryNavigation] = useState(0);
  const api: PerigeeApi = useMemo(() => (fixtureMode ? createFixtureApi() : createHttpApi()), [fixtureMode]);
  // Bounded session cache, keyed by the full signed cutout request.
  const frameCache = useRef(new Map<string, FrameRecord>());
  // Native in-page links can emit popstate. A hash jump must not restart a
  // completed archive query or reset its selected image and notebook.
  const routeLocation = useRef(window.location.pathname + window.location.search);

  useEffect(() => {
    const onPop = () => {
      const location = window.location.pathname + window.location.search;
      if (location === routeLocation.current) return;
      routeLocation.current = location;
      setRoute(parseRoute(window.location.search));
      setFixtureMode(initialFixtureMode());
      setQueryNavigation((n) => n + 1);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const navigate = useCallback(
    (next: Route, replace = false, fixtures = fixtureMode) => {
      const url = `${window.location.pathname}${routeToSearch(next, fixtures)}`;
      if (replace) window.history.replaceState(null, "", url);
      else window.history.pushState(null, "", url);
      routeLocation.current = url;
      if (fixtures !== fixtureMode) setFixtureMode(fixtures);
      setRoute(next);
      if (!replace && next.view === "query") setQueryNavigation((n) => n + 1);
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
    routeLocation.current = window.location.pathname + window.location.search;
    setFixtureMode(on);
  };
  const useFixture = () => setFixtures(true);

  // Move focus to the new view's heading so keyboard and screen reader users
  // land in context. A preset renders its heading only once its frames have
  // loaded, so focus follows the heading when it mounts.
  const mainRef = useRef<HTMLElement>(null);
  const pendingInvestigations = useRef(window.location.hash === "#investigations");
  const routeKey = route.view === "preset" ? `preset:${route.presetId}:${route.caseId ?? "default"}` : route.view;
  useEffect(() => (mainRef.current && !(route.view === "home" && pendingInvestigations.current) ? focusHeadingIn(mainRef.current) : undefined), [routeKey]);
  const focusInvestigations = () => {
    const heading = document.getElementById("presets-h");
    heading?.setAttribute("tabindex", "-1");
    heading?.scrollIntoView({ block: "start" });
    heading?.focus({ preventScroll: true });
    window.history.replaceState(null, "", `${window.location.pathname}${fixtureMode ? "?fixtures=1" : ""}#investigations`);
  };
  useEffect(() => {
    if (route.view === "home" && pendingInvestigations.current) {
      pendingInvestigations.current = false;
      focusInvestigations();
    }
  }, [route]);

  const pendingEvidence = useRef(window.location.hash === "#my-evidence");
  const focusEvidence = () => {
    const heading = document.getElementById("saved-h");
    heading?.scrollIntoView({ block: "start" });
    heading?.focus({ preventScroll: true });
  };
  useEffect(() => {
    if (route.view === "home" && pendingEvidence.current) {
      pendingEvidence.current = false;
      focusEvidence();
    }
  }, [route]);

  // This navigation always opens the saved collection, not the current notebook.
  const goToEvidence = (e: React.MouseEvent) => {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    if (route.view === "home") return focusEvidence();
    pendingEvidence.current = true;
    navigate({ view: "home" });
  };

  const openQueryAt = (preset: PresetDescriptor) =>
    navigate({
      view: "query",
      ra: String(preset.query_center?.ra_deg ?? ""),
      dec: String(preset.query_center?.dec_deg ?? ""),
      fov: String(preset.default_fov_arcmin ?? 6),
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
      <header className={`topbar${route.view === "home" ? " landing-nav" : ""}`}>
        <a
          href={`${window.location.pathname}${fixtureMode ? "?fixtures=1" : ""}`}
          className="brand"
          aria-label="Perigee home"
          onClick={(e) => {
            if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
            e.preventDefault();
            navigate({ view: "home" });
          }}
        >
          <BrandMark />
          perigee
        </a>
        <nav aria-label="Main">
          <ul>
            <li>
              <a
                href={`/${fixtureMode ? "?fixtures=1" : ""}#investigations`}
                className="wide-only"
                aria-current={route.view === "home" ? "page" : undefined}
                onClick={(e) => {
                  if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
                  e.preventDefault();
                  if (route.view === "home") return focusInvestigations();
                  pendingInvestigations.current = true;
                  navigate({ view: "home" });
                }}
              >
                Investigations
              </a>
            </li>
            <li>
              <a
                href={routeToSearch({ view: "query" }, fixtureMode)}
                aria-current={route.view === "query" ? "page" : undefined}
                onClick={(e) => {
                  if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
                  e.preventDefault();
                  navigate({ view: "query" });
                }}
              >
                {/* One text node per breakpoint: an inline span with a leading space
                    produced "Search  coordinates" in the accessible name. */}
                <span className="wide-only">Search archive</span>
                <span className="phone-only">Search</span>
              </a>
            </li>
            <li>
              <a href={`${window.location.pathname}${fixtureMode ? "?fixtures=1" : ""}#my-evidence`} onClick={goToEvidence}>
                My evidence
              </a>
            </li>
          </ul>
        </nav>
      </header>

      <main id="main" className={route.view === "home" ? "landing-main" : "investigation-main"} ref={mainRef} tabIndex={-1}>
        {route.view === "home" && (
          <Home
            api={api}
            onOpenPreset={(id) => navigate({ view: "preset", presetId: id })}
            onOpenQuery={() => navigate({ view: "query" })}
            onOpenRoute={(next, fixtures) => navigate(next, false, fixtures)}
            onUseFixture={useFixture}
          />
        )}
        {route.view === "preset" && (
          <PresetInvestigation
            key={`${api.mode}:${route.presetId}:${route.caseId ?? "default"}`}
            api={api}
            presetId={route.presetId}
            caseId={route.caseId}
            onUseFixture={useFixture}
            onQueryPosition={openQueryAt}
            onOpenPreset={(id) => navigate({ view: "preset", presetId: id })}
            onOpenQuery={() => navigate({ view: "query" })}
          />
        )}
        {route.view === "query" && (
          <QueryInvestigation
            key={`${api.mode}:query:${queryNavigation}`}
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
                  limit: String(q.limit),
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
          SPHEREx archive
        </a>
        <p className="footer-ai">
          <a href={AI_USE_URL} target="_blank" rel="noreferrer">
            AI use disclosure
          </a>
        </p>
      </footer>
    </>
  );
}
