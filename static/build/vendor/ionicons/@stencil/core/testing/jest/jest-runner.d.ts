import type * as d from '@stencil/core/internal';
import type { ConfigFlags } from '../../cli/config-flags';
export declare function runJest(config: d.ValidatedConfig, env: d.E2EProcessEnv): Promise<boolean>;
/**
 * Creates a Stencil test runner
 * @returns the test runner
 */
export declare function createTestRunner(): any;
export declare function includeTestFile(testPath: string, env: d.E2EProcessEnv): boolean;
export declare function getEmulateConfigs(testing: d.TestingConfig, flags: ConfigFlags): d.EmulateConfig[];
