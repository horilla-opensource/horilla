import type { PlaywrightTestArgs, PlaywrightTestOptions, PlaywrightWorkerArgs, PlaywrightWorkerOptions, TestInfo } from '@playwright/test';
import type { E2EPage } from './playwright-declarations';
type CustomFixtures = {
  page: E2EPage;
};
/**
 * Extends the base `page` test figure within Playwright.
 * @param page The page to extend.
 * @param testInfo The test info.
 * @returns The modified playwright page with extended functionality.
 */
export declare function extendPageFixture(page: E2EPage, testInfo: TestInfo): Promise<E2EPage>;
export declare const test: import("@playwright/test").TestType<PlaywrightTestArgs & PlaywrightTestOptions & CustomFixtures, PlaywrightWorkerArgs & PlaywrightWorkerOptions>;
export {};
