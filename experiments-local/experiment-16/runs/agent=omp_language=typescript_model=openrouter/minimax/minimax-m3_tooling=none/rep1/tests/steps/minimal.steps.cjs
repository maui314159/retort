console.log('LOADING minimal.steps.cjs');
module.exports = function () {
  console.log('REGISTERING STEPS, this=', typeof this);
  this.Given('the dataset is loaded', function () {
    console.log('STEP EXECUTED');
  });
};
