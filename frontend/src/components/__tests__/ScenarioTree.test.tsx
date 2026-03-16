import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import ScenarioTree from '../simulator/ScenarioTree';

vi.mock('../../services/api', () => ({
  getSimulationHistory: vi.fn(),
}));

import { getSimulationHistory } from '../../services/api';

const mockedGetHistory = getSimulationHistory as ReturnType<typeof vi.fn>;

const mockHistory = [
  {
    id: 'sim-1',
    scenario_type: 'drop_course',
    parameters: { course_code: 'CS 225' },
    result: {
      new_graduation: 'Fall 2027',
      semesters_added: 1,
      risk_level: 'medium',
      affected_courses: [
        { code: 'CS 374', original_semester: 5, new_semester: 6 },
      ],
      constraint_checks: [
        { label: 'Credit cap', passed: true, severity: 'ok' },
      ],
      recommendations: ['Take CS 225 in summer'],
    },
    explanation: 'Dropping CS 225 delays graduation by one semester.',
    parent_simulation_id: null,
  },
  {
    id: 'sim-2',
    scenario_type: 'block_semester',
    parameters: { semester: 5 },
    result: {
      new_graduation: 'Spring 2028',
      semesters_added: 2,
      risk_level: 'high',
      affected_courses: [],
      constraint_checks: [],
      recommendations: [],
    },
    explanation: 'Blocking semester 5 pushes back significantly.',
    parent_simulation_id: 'sim-1',
  },
];

describe('ScenarioTree', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Scenario Tree heading', async () => {
    mockedGetHistory.mockResolvedValue(mockHistory);
    render(<ScenarioTree sessionId="s1" />);
    await waitFor(() => {
      expect(screen.getByText('Scenario Tree')).toBeInTheDocument();
    });
  });

  it('renders Current Plan root node', async () => {
    mockedGetHistory.mockResolvedValue(mockHistory);
    render(<ScenarioTree sessionId="s1" currentGraduation="Spring 2027" />);
    await waitFor(() => {
      expect(screen.getByText('Current Plan')).toBeInTheDocument();
    });
  });

  it('renders scenario labels from history', async () => {
    mockedGetHistory.mockResolvedValue(mockHistory);
    render(<ScenarioTree sessionId="s1" />);
    await waitFor(() => {
      expect(screen.getByText('Drop Course')).toBeInTheDocument();
      expect(screen.getByText('Block Semester')).toBeInTheDocument();
    });
  });

  it('shows semesters added indicator for scenarios', async () => {
    mockedGetHistory.mockResolvedValue(mockHistory);
    render(<ScenarioTree sessionId="s1" />);
    await waitFor(() => {
      // Semester change indicators appear as "+N sem" on tree nodes
      expect(screen.getByText(/\+1 sem/)).toBeInTheDocument();
      expect(screen.getByText(/\+2 sem/)).toBeInTheDocument();
    });
  });

  it('shows risk level badges', async () => {
    mockedGetHistory.mockResolvedValue(mockHistory);
    render(<ScenarioTree sessionId="s1" />);
    await waitFor(() => {
      expect(screen.getByText('medium')).toBeInTheDocument();
      expect(screen.getByText('high')).toBeInTheDocument();
    });
  });

  it('shows empty state when no history', async () => {
    mockedGetHistory.mockResolvedValue([]);
    render(<ScenarioTree sessionId="s1" />);
    await waitFor(() => {
      expect(screen.getByText(/run simulations to see/i)).toBeInTheDocument();
    });
  });

  it('renders nothing while loading', () => {
    mockedGetHistory.mockReturnValue(new Promise(() => {}));
    const { container } = render(<ScenarioTree sessionId="s1" />);
    // ScenarioTree returns null during loading
    expect(container.firstChild).toBeNull();
  });

  it('calls getSimulationHistory with sessionId', async () => {
    mockedGetHistory.mockResolvedValue([]);
    render(<ScenarioTree sessionId="test-session" />);
    await waitFor(() => {
      expect(mockedGetHistory).toHaveBeenCalledWith('test-session');
    });
  });
});
