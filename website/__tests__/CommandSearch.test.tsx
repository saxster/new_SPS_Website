import { describe, it, expect } from 'vitest';

describe('CommandSearch', () => {
    it('should import without JSX syntax errors', async () => {
        // This test verifies the component has valid JSX syntax
        // It will fail if there are unescaped characters like '>'
        const module = await import('../src/components/CommandSearch');
        expect(module).toBeDefined();
    });
});
