import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CitationCard } from './CitationCard';

// Setup jest-dom matchers
import '@testing-library/jest-dom/vitest';

const mockCitations = [
  {
    index: 1,
    content: 'This product has a 4.5 star rating with over 1000 reviews.',
    source: 'products.pdf',
    score: 0.92,
  },
  {
    index: 2,
    content: 'The price ranges from $29.99 to $99.99 depending on size.',
    source: 'catalog.csv',
    score: 0.75,
  },
];

describe('CitationCard', () => {
  it('renders nothing when citations is empty', () => {
    const { container } = render(<CitationCard citations={[]} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders nothing when citations is null', () => {
    const { container } = render(<CitationCard citations={null} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders citation items when provided', () => {
    render(<CitationCard citations={mockCitations} />);
    expect(screen.getByText('参考来源')).toBeInTheDocument();
    expect(screen.getByText('[1]')).toBeInTheDocument();
    expect(screen.getByText('[2]')).toBeInTheDocument();
  });

  it('displays citation content', () => {
    render(<CitationCard citations={mockCitations} />);
    expect(screen.getByText(/This product has a 4.5 star rating/)).toBeInTheDocument();
  });

  it('shows source file name', () => {
    render(<CitationCard citations={mockCitations} />);
    expect(screen.getByText('products.pdf')).toBeInTheDocument();
    expect(screen.getByText('catalog.csv')).toBeInTheDocument();
  });

  it('displays relevance score as percentage', () => {
    render(<CitationCard citations={mockCitations} />);
    expect(screen.getByText(/92%/)).toBeInTheDocument();
    expect(screen.getByText(/75%/)).toBeInTheDocument();
  });
});
