// Cucumber configuration: CommonJS step definitions under tests/steps,
// Gherkin features under features/.
export default {
  require: ['tests/steps/**/*.steps.cjs'],
  paths: ['features'],
  format: ['progress', 'html:cucumber-report.html'],
  publishQuiet: true,
  timeout: 30000
};
