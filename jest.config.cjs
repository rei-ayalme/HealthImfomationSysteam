module.exports = {
  testEnvironment: 'node',
  roots: ['<rootDir>/__tests__/integration/deepanalyze'],
  collectCoverageFrom: ['deepanalyze/**/*.js', 'src/deepanalyze/agent/**/*.js'],
  coverageThreshold: {
    global: {
      lines: 80
    }
  }
};
