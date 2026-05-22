import os
import glob

files = glob.glob('src/components/**/*.test.tsx', recursive=True)

old_mock = """vi.mock('axios', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), put: vi.fn() }
}));"""

new_mock = """vi.mock('axios', () => {
  const mockAxiosInstance = { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), put: vi.fn() };
  return {
    default: {
      ...mockAxiosInstance,
      create: vi.fn(() => mockAxiosInstance)
    }
  };
});"""

fixed_count = 0
for filepath in files:
    with open(filepath, 'r') as f:
        content = f.read()
    
    if old_mock in content:
        content = content.replace(old_mock, new_mock)
        with open(filepath, 'w') as f:
            f.write(content)
        fixed_count += 1

print(f"Fixed {fixed_count} test files.")
