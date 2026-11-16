import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../src/api/client";
import { SearchFailureRecovery } from "../src/components/QueryInvestigation";
import { ErrorBlock } from "../src/components/common";

afterEach(() => vi.unstubAllEnvs());

const failure = new ApiError({ code: "UPSTREAM_TIMEOUT", message: "Archive timed out", retryable: true });

describe("archive failure recovery", () => {
  it("offers retry and prepared NASA investigations in production without switching to fixtures", () => {
    vi.stubEnv("DEV", false);
    const retry = vi.fn();
    const useFixture = vi.fn();
    const html = renderToStaticMarkup(createElement(SearchFailureRecovery, {
      error: failure, onRetry: retry, onUseFixture: useFixture,
    }));
    expect(html).toContain("Try again");
    expect(html).toContain('href="/#investigations"');
    expect(html).toContain("Open prepared NASA investigations");
    expect(html).toContain("your notes are kept");
    expect(html).not.toContain("Use development fixture");
    expect(retry).not.toHaveBeenCalled();
    expect(useFixture).not.toHaveBeenCalled();
  });

  it("hides the fixture action centrally for every production error block", () => {
    vi.stubEnv("DEV", false);
    const html = renderToStaticMarkup(createElement(ErrorBlock, {
      title: "The images could not be loaded.", error: failure,
      onRetry() {}, onUseFixture() {}, onChooseInvestigation() {},
    }));
    expect(html).toContain("Choose an investigation");
    expect(html).toContain("Try again");
    expect(html).not.toContain("Use development fixture");
  });

  it("keeps the explicitly labelled fixture tool available during development", () => {
    vi.stubEnv("DEV", true);
    const html = renderToStaticMarkup(createElement(SearchFailureRecovery, {
      error: failure, onRetry() {}, onUseFixture() {},
    }));
    expect(html).toContain("Use development fixture (not NASA data)");
    expect(html).toContain('href="/#investigations"');
  });
});
