"use strict";
var dgvis = dgvis || {};

dgvis.menu = (function(){
  var my = {};

  var departments = [];


  function buildMenu(departments, orgSelect) {
    // Flatten tree
    var items = [{
      name: 'Departments'
    }];

    _.each(departments, function(d) {
      items.push({
        name: d.name
      });

      _.each(d.organisations, function(org) {
        items.push({
          name: '- ' + org.name,
          filename: org.filename
        });
      });
    });

    d3.select('.menu .departments')
      .selectAll('option')
      .data(items)
      .enter()
      .append('option')
      .text(function(d) {
        return d.name;
      })
      .attr('disabled', function(d) {
        return d.filename !== undefined || d.name === 'Departments' ? null : 'disabled';
      });

    d3.select('.menu .departments')
      .on('change', function(d) {
        var file = this.selectedOptions[0].__data__.filename;
        orgSelect(file);
        $(this).blur(); // so that we can immediately scroll with spacebar
      });
  }

  my.init = function(ready, orgSelect) {
    d3.json('../wrangling/output/depts_and_orgs.json', function(err, data) {
      // console.log(data);
      departments = data;

      buildMenu(departments, orgSelect);
      ready();
    });
  }

  return my;
})();
