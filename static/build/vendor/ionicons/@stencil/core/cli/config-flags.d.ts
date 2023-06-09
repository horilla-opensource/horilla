import type { LogLevel, TaskCommand } from '../internal/index';
/**
 * All the Boolean options supported by the Stencil CLI
 */
export declare const BOOLEAN_CLI_FLAGS: readonly ["build", "cache", "checkVersion", "ci", "compare", "debug", "dev", "devtools", "docs", "e2e", "es5", "esm", "headless", "help", "log", "open", "prerender", "prerenderExternal", "prod", "profile", "serviceWorker", "screenshot", "serve", "skipNodeCheck", "spec", "ssr", "stats", "updateScreenshot", "verbose", "version", "watch", "all", "automock", "bail", "changedFilesWithAncestor", "clearCache", "clearMocks", "collectCoverage", "color", "colors", "coverage", "detectLeaks", "detectOpenHandles", "errorOnDeprecated", "expand", "findRelatedTests", "forceExit", "init", "injectGlobals", "json", "lastCommit", "listTests", "logHeapUsage", "noStackTrace", "notify", "onlyChanged", "onlyFailures", "passWithNoTests", "resetMocks", "resetModules", "restoreMocks", "runInBand", "runTestsByPath", "showConfig", "silent", "skipFilter", "testLocationInResults", "updateSnapshot", "useStderr", "watchAll", "watchman"];
/**
 * All the Number options supported by the Stencil CLI
 */
export declare const NUMBER_CLI_FLAGS: readonly ["port", "maxConcurrency", "testTimeout"];
/**
 * All the String options supported by the Stencil CLI
 */
export declare const STRING_CLI_FLAGS: readonly ["address", "config", "docsApi", "docsJson", "emulate", "root", "screenshotConnector", "cacheDirectory", "changedSince", "collectCoverageFrom", "coverageDirectory", "coverageThreshold", "env", "filter", "globalSetup", "globalTeardown", "globals", "haste", "moduleNameMapper", "notifyMode", "outputFile", "preset", "prettierPath", "resolver", "rootDir", "runner", "testEnvironment", "testEnvironmentOptions", "testFailureExitCode", "testNamePattern", "testResultsProcessor", "testRunner", "testSequencer", "testURL", "timers", "transform"];
export declare const STRING_ARRAY_CLI_FLAGS: readonly ["collectCoverageOnlyFrom", "coveragePathIgnorePatterns", "coverageReporters", "moduleDirectories", "moduleFileExtensions", "modulePathIgnorePatterns", "modulePaths", "projects", "reporters", "roots", "selectProjects", "setupFiles", "setupFilesAfterEnv", "snapshotSerializers", "testMatch", "testPathIgnorePatterns", "testPathPattern", "testRegex", "transformIgnorePatterns", "unmockedModulePathPatterns", "watchPathIgnorePatterns"];
/**
 * All the CLI arguments which may have string or number values
 *
 * `maxWorkers` is an argument which is used both by Stencil _and_ by Jest,
 * which means that we need to support parsing both string and number values.
 */
export declare const STRING_NUMBER_CLI_FLAGS: readonly ["maxWorkers"];
/**
 * All the LogLevel-type options supported by the Stencil CLI
 *
 * This is a bit silly since there's only one such argument atm,
 * but this approach lets us make sure that we're handling all
 * our arguments in a type-safe way.
 */
export declare const LOG_LEVEL_CLI_FLAGS: readonly ["logLevel"];
/**
 * A type which gives the members of a `ReadonlyArray<string>` as
 * an enum-like type which can be used for e.g. keys in a `Record`
 * (as in the `AliasMap` type below)
 */
type ArrayValuesAsUnion<T extends ReadonlyArray<string>> = T[number];
export type BooleanCLIFlag = ArrayValuesAsUnion<typeof BOOLEAN_CLI_FLAGS>;
export type StringCLIFlag = ArrayValuesAsUnion<typeof STRING_CLI_FLAGS>;
export type StringArrayCLIFlag = ArrayValuesAsUnion<typeof STRING_ARRAY_CLI_FLAGS>;
export type NumberCLIFlag = ArrayValuesAsUnion<typeof NUMBER_CLI_FLAGS>;
export type StringNumberCLIFlag = ArrayValuesAsUnion<typeof STRING_NUMBER_CLI_FLAGS>;
export type LogCLIFlag = ArrayValuesAsUnion<typeof LOG_LEVEL_CLI_FLAGS>;
export type KnownCLIFlag = BooleanCLIFlag | StringCLIFlag | StringArrayCLIFlag | NumberCLIFlag | StringNumberCLIFlag | LogCLIFlag;
type AliasMap = Partial<Record<string, KnownCLIFlag>>;
/**
 * For a small subset of CLI options we support a short alias e.g. `'h'` for `'help'`
 */
export declare const CLI_FLAG_ALIASES: AliasMap;
/**
 * A regular expression which can be used to match a CLI flag for one of our
 * short aliases.
 */
export declare const CLI_FLAG_REGEX: RegExp;
/**
 * Given two types `K` and `T` where `K` extends `ReadonlyArray<string>`,
 * construct a type which maps the strings in `K` as keys to values of type `T`.
 *
 * Because we use types derived this way to construct an interface (`ConfigFlags`)
 * for which we want optional keys, we make all the properties optional (w/ `'?'`)
 * and possibly null.
 */
type ObjectFromKeys<K extends ReadonlyArray<string>, T> = {
    [key in K[number]]?: T | null;
};
/**
 * Type containing the possible Boolean configuration flags, to be included
 * in ConfigFlags, below
 */
type BooleanConfigFlags = ObjectFromKeys<typeof BOOLEAN_CLI_FLAGS, boolean>;
/**
 * Type containing the possible String configuration flags, to be included
 * in ConfigFlags, below
 */
type StringConfigFlags = ObjectFromKeys<typeof STRING_CLI_FLAGS, string>;
/**
 * Type containing the possible String Array configuration flags. This is
 * one of the 'constituent types' for `ConfigFlags`.
 */
type StringArrayConfigFlags = ObjectFromKeys<typeof STRING_ARRAY_CLI_FLAGS, string[]>;
/**
 * Type containing the possible numeric configuration flags, to be included
 * in ConfigFlags, below
 */
type NumberConfigFlags = ObjectFromKeys<typeof NUMBER_CLI_FLAGS, number>;
/**
 * Type containing the configuration flags which may be set to either string
 * or number values.
 */
type StringNumberConfigFlags = ObjectFromKeys<typeof STRING_NUMBER_CLI_FLAGS, string | number>;
/**
 * Type containing the possible LogLevel configuration flags, to be included
 * in ConfigFlags, below
 */
type LogLevelFlags = ObjectFromKeys<typeof LOG_LEVEL_CLI_FLAGS, LogLevel>;
/**
 * The configuration flags which can be set by the user on the command line.
 * This interface captures both known arguments (which are enumerated and then
 * parsed according to their types) and unknown arguments which the user may
 * pass at the CLI.
 *
 * Note that this interface is constructed by extending `BooleanConfigFlags`,
 * `StringConfigFlags`, etc. These types are in turn constructed from types
 * extending `ReadonlyArray<string>` which we declare in another module. This
 * allows us to record our known CLI arguments in one place, using a
 * `ReadonlyArray<string>` to get both a type-level representation of what CLI
 * options we support and a runtime list of strings which can be used to match
 * on actual flags passed by the user.
 */
export interface ConfigFlags extends BooleanConfigFlags, StringConfigFlags, StringArrayConfigFlags, NumberConfigFlags, StringNumberConfigFlags, LogLevelFlags {
    task: TaskCommand | null;
    args: string[];
    knownArgs: string[];
    unknownArgs: string[];
}
/**
 * Helper function for initializing a `ConfigFlags` object. Provide any overrides
 * for default values and off you go!
 *
 * @param init an object with any overrides for default values
 * @returns a complete CLI flag object
 */
export declare const createConfigFlags: (init?: Partial<ConfigFlags>) => ConfigFlags;
export {};
