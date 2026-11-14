import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      {fixtureMode && (
        <div className="fixture-banner" role="note">
          <strong>Development fixture — not NASA data.</strong> Images are placeholders; nothing comes from the API.{" "}
          <button type="button" className="link" onClick={() => setFixtures(false)}>
            Switch to the live API
          </button>
        </div>
      )}
      <header className="site-header">
        <a
          href={`${window.location.pathname}${fixtureMode ? "?fixtures=1" : ""}`}
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            navigate({ view: "home" });
          }}
        >
          Perigee
        </a>
        <nav aria-label="Main">
          <ul>
            <li>
              <a
                href="?"
                aria-current={route.view === "home" ? "page" : undefined}
                onClick={(e) => {
                  e.preventDefault();
                  navigate({ view: "home" });
                }}
              >
                Targets
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
                Search coordinates
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
        <p>
          Images: SPHEREx, NASA/IPAC Infrared Science Archive. Perigee shows display images for visual comparison;
          it does not measure brightness or position.
        </p>
        <p className="muted">
          Perigee {__APP_VERSION__} · data source: {fixtureMode ? "development fixture" : "live API"}
          {!fixtureMode && import.meta.env.DEV && (
            <>
              {" · "}
              <button type="button" className="link" onClick={useFixture}>
                Use development fixture
              </button>
            </>
          )}
        </p>
      </footer>
    </>
  );
}
