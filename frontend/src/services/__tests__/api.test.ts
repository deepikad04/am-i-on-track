import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// We test the api module's exported functions by mocking axios
vi.mock('axios', () => {
  const instance = {
    get: vi.fn(),
    post: vi.fn(),
    defaults: { headers: { common: {} } },
  };
  return {
    default: { create: () => instance, ...instance },
  };
});

import api, {
  getDegreeData,
  updateProgress,
  getSimulationResult,
  checkHealth,
} from '../api';

describe('API service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('getDegreeData calls GET /degree/:sessionId', async () => {
    const mockData = { courses: [], requirements: [] };
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: mockData });

    const result = await getDegreeData('session-123');
    expect(api.get).toHaveBeenCalledWith('/degree/session-123');
    expect(result).toEqual(mockData);
  });

  it('updateProgress calls POST with correct payload', async () => {
    const mockData = { status: 'updated' };
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data: mockData });

    const result = await updateProgress('s1', ['CS101', 'CS102'], 3);
    expect(api.post).toHaveBeenCalledWith('/degree/s1/progress', {
      completed_courses: ['CS101', 'CS102'],
      current_semester: 3,
    });
    expect(result).toEqual(mockData);
  });

  it('getSimulationResult calls GET /simulate/:id/result', async () => {
    const mockData = { schedule: [] };
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: mockData });

    const result = await getSimulationResult('sim-456');
    expect(api.get).toHaveBeenCalledWith('/simulate/sim-456/result');
    expect(result).toEqual(mockData);
  });

  it('checkHealth calls GET /health', async () => {
    const mockData = { status: 'ok' };
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: mockData });

    const result = await checkHealth();
    expect(api.get).toHaveBeenCalledWith('/health');
    expect(result).toEqual(mockData);
  });
});
