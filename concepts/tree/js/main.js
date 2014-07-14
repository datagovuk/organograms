(function() {

  var departments = [];


  function buildMenu(departments) {
    
  }

  d3.json('../wrangling/output/depts_and_orgs.json', function(err, data) {
    console.log(data);
    departments = data;

    buildMenu(departments);
    // updateLayerStack(orgData, 0);
    // layerStack.push(orgData);

    // update();
  });


})();
