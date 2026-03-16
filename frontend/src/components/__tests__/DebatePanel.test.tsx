import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import DebatePanel from '../simulator/DebatePanel';

// Mock the API module
vi.mock('../../services/api', () => ({
  runDebate: vi.fn(),
}));

import { runDebate } from '../../services/api';

const mockedRunDebate = runDebate as ReturnType<typeof vi.fn>;

describe('DebatePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders debate header and start button', () => {
    render(<DebatePanel sessionId="s1" />);
    expect(screen.getByText('Agent Debate')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /start agent debate/i })).toBeInTheDocument();
  });

  it('has correct ARIA region role and label', () => {
    render(<DebatePanel sessionId="s1" />);
    const region = screen.getByRole('region', { name: /agent debate/i });
    expect(region).toBeInTheDocument();
  });

  it('shows description text about two AI advisors', () => {
    render(<DebatePanel sessionId="s1" />);
    expect(screen.getByText(/two ai advisors argue opposing strategies/i)).toBeInTheDocument();
  });

  it('disables button and shows loading state while running', async () => {
    // Make runDebate hang indefinitely
    mockedRunDebate.mockReturnValue(new Promise(() => {}));

    render(<DebatePanel sessionId="s1" />);
    fireEvent.click(screen.getByRole('button', { name: /start agent debate/i }));

    await waitFor(() => {
      const btn = screen.getByRole('button', { name: /debate in progress/i });
      expect(btn).toBeDisabled();
      expect(btn).toHaveAttribute('aria-busy', 'true');
    });
    expect(screen.getByText('Debating…')).toBeInTheDocument();
  });

  it('renders Fast Track and Safe Path proposals on success', async () => {
    mockedRunDebate.mockResolvedValue({
      fast: 'Take 18 credits next semester',
      safe: 'Keep it at 15 credits',
    });

    render(<DebatePanel sessionId="s1" />);
    fireEvent.click(screen.getByRole('button', { name: /start agent debate/i }));

    await waitFor(() => {
      expect(screen.getByText('Fast Track')).toBeInTheDocument();
      expect(screen.getByText('Safe Path')).toBeInTheDocument();
      expect(screen.getByText('Take 18 credits next semester')).toBeInTheDocument();
      expect(screen.getByText('Keep it at 15 credits')).toBeInTheDocument();
    });
  });

  it('shows error message when debate fails', async () => {
    mockedRunDebate.mockRejectedValue(new Error('Network error'));

    render(<DebatePanel sessionId="s1" />);
    fireEvent.click(screen.getByRole('button', { name: /start agent debate/i }));

    await waitFor(() => {
      expect(screen.getByText(/debate failed/i)).toBeInTheDocument();
    });
  });

  it('re-enables button after debate completes', async () => {
    mockedRunDebate.mockResolvedValue({ fast: 'F', safe: 'S' });

    render(<DebatePanel sessionId="s1" />);
    fireEvent.click(screen.getByRole('button', { name: /start agent debate/i }));

    await waitFor(() => {
      const btn = screen.getByRole('button', { name: /start agent debate/i });
      expect(btn).not.toBeDisabled();
    });
  });

  it('passes sessionId to runDebate', async () => {
    mockedRunDebate.mockResolvedValue({ fast: 'F', safe: 'S' });

    render(<DebatePanel sessionId="test-session-42" />);
    fireEvent.click(screen.getByRole('button', { name: /start agent debate/i }));

    await waitFor(() => {
      expect(mockedRunDebate).toHaveBeenCalledWith('test-session-42', expect.any(Function));
    });
  });
});
