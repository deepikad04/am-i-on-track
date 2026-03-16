import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import ImpactReportPanel from '../impact/ImpactReportPanel';

const mockMetrics = {
  total_credits: 128,
  completed_credits: 64,
  remaining_credits: 64,
  estimated_semesters_remaining: 4,
  semesters_saved: 1,
  estimated_tuition_saved: 15000,
  advisor_hours_saved: 8,
  risk_level: 'medium' as const,
  bottleneck_courses: ['CS 374', 'CS 421'],
  on_track: true,
  credits_per_semester_avg: 15,
  completion_percentage: 50,
};

const mockPolicy = {
  violations: [],
  passed: true,
  summary: 'All policies satisfied',
};

vi.mock('../../services/api', () => ({
  getImpactReport: vi.fn(),
  getPolicyCheck: vi.fn(),
  getAdvisingSummary: vi.fn(),
  generateRoadmapImage: vi.fn(),
}));

import { getImpactReport, getPolicyCheck, getAdvisingSummary, generateRoadmapImage } from '../../services/api';

// Also mock the child AgentMemoryPanel to isolate tests
vi.mock('../impact/AgentMemoryPanel', () => ({
  default: () => <div data-testid="agent-memory-panel" />,
}));

const mockedGetImpact = getImpactReport as ReturnType<typeof vi.fn>;
const mockedGetPolicy = getPolicyCheck as ReturnType<typeof vi.fn>;
const mockedGetSummary = getAdvisingSummary as ReturnType<typeof vi.fn>;
const mockedGenRoadmap = generateRoadmapImage as ReturnType<typeof vi.fn>;

describe('ImpactReportPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetImpact.mockResolvedValue(mockMetrics);
    mockedGetPolicy.mockResolvedValue(mockPolicy);
  });

  it('shows loading skeleton initially', () => {
    // Never resolve to keep loading state
    mockedGetImpact.mockReturnValue(new Promise(() => {}));
    mockedGetPolicy.mockReturnValue(new Promise(() => {}));

    const { container } = render(<ImpactReportPanel sessionId="s1" />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders impact report header after loading', async () => {
    render(<ImpactReportPanel sessionId="s1" />);
    await waitFor(() => {
      expect(screen.getByText('Impact Report')).toBeInTheDocument();
    });
  });

  it('displays completion percentage', async () => {
    render(<ImpactReportPanel sessionId="s1" />);
    await waitFor(() => {
      expect(screen.getByText('50%')).toBeInTheDocument();
      expect(screen.getByText('64 credits done')).toBeInTheDocument();
      expect(screen.getByText('64 remaining')).toBeInTheDocument();
    });
  });

  it('displays all four metric cards', async () => {
    render(<ImpactReportPanel sessionId="s1" />);
    await waitFor(() => {
      expect(screen.getByText('Semesters Saved')).toBeInTheDocument();
      expect(screen.getByText('Tuition Saved')).toBeInTheDocument();
      expect(screen.getByText('Advisor Hours Saved')).toBeInTheDocument();
      expect(screen.getByText('On Track')).toBeInTheDocument();
    });
  });

  it('displays tuition saved formatted with dollar sign', async () => {
    render(<ImpactReportPanel sessionId="s1" />);
    await waitFor(() => {
      expect(screen.getByText('$15,000')).toBeInTheDocument();
    });
  });

  it('shows risk level badge', async () => {
    render(<ImpactReportPanel sessionId="s1" />);
    await waitFor(() => {
      expect(screen.getByText('MEDIUM')).toBeInTheDocument();
    });
  });

  it('shows bottleneck courses', async () => {
    render(<ImpactReportPanel sessionId="s1" />);
    await waitFor(() => {
      expect(screen.getByText('CS 374')).toBeInTheDocument();
      expect(screen.getByText('CS 421')).toBeInTheDocument();
    });
  });

  it('shows Export Summary and Roadmap Image buttons', async () => {
    render(<ImpactReportPanel sessionId="s1" />);
    await waitFor(() => {
      expect(screen.getByText('Export Summary')).toBeInTheDocument();
      expect(screen.getByText('Roadmap Image')).toBeInTheDocument();
    });
  });

  it('shows At Risk status when not on track', async () => {
    mockedGetImpact.mockResolvedValue({ ...mockMetrics, on_track: false });
    render(<ImpactReportPanel sessionId="s1" />);
    await waitFor(() => {
      expect(screen.getByText('At Risk')).toBeInTheDocument();
    });
  });

  it('shows policy violations when present', async () => {
    mockedGetPolicy.mockResolvedValue({
      violations: [
        { rule: 'Credit Cap', severity: 'error', detail: 'Semester 5 exceeds 18 credits', suggestion: 'Move one course' },
      ],
      passed: false,
      summary: '1 violation found',
    });
    render(<ImpactReportPanel sessionId="s1" />);
    await waitFor(() => {
      expect(screen.getByText('Credit Cap')).toBeInTheDocument();
      expect(screen.getByText('Semester 5 exceeds 18 credits')).toBeInTheDocument();
    });
  });

  it('shows all policies satisfied when no violations', async () => {
    render(<ImpactReportPanel sessionId="s1" />);
    await waitFor(() => {
      expect(screen.getByText(/your plan is compliant/i)).toBeInTheDocument();
    });
  });
});
