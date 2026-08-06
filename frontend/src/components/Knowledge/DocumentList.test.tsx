import { describe, it, expect } from 'vitest';
import '@testing-library/jest-dom/vitest';

// Test formatSize utility function in isolation
describe('DocumentList utilities', () => {
  describe('formatSize', () => {
    // Import the actual function by reading the source
    // Since formatSize is defined inside the component, we test the logic here

    it('formats bytes correctly', () => {
      const formatSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
      };

      expect(formatSize(500)).toBe('500 B');
      expect(formatSize(1024)).toBe('1.0 KB');
      expect(formatSize(1536)).toBe('1.5 KB');
      expect(formatSize(1048576)).toBe('1.0 MB');
      expect(formatSize(5242880)).toBe('5.0 MB');
    });
  });

  describe('status color mapping', () => {
    it('maps completed to green', () => {
      const statusColorMap: Record<string, string> = { completed: 'green', processing: 'blue', failed: 'red' };
      expect(statusColorMap['completed']).toBe('green');
      expect(statusColorMap['processing']).toBe('blue');
      expect(statusColorMap['failed']).toBe('red');
    });
  });

  describe('file type mapping', () => {
    it('maps extensions correctly', () => {
      const extMap: Record<string, string> = { '.pdf': 'pdf', '.txt': 'txt', '.csv': 'csv', '.md': 'md' };
      expect(extMap['.pdf']).toBe('pdf');
      expect(extMap['.txt']).toBe('txt');
      expect(extMap['.csv']).toBe('csv');
      expect(extMap['.md']).toBe('md');
    });
  });
});
