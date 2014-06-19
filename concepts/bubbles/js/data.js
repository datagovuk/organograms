"use strict";
var dg = dg || {};

dg.data = (function(){
  var my = {};

  var data = {
    junior: [],
    senior: []
  };

  my.init = function(csvJ, csvS) {
    data.junior = csvJ;
    data.senior = csvS;
  }

  my.headTotals = function(id) {
    // Recursive headcount

    // TODO there seems to be a bug in this - with Natural England data, headTotal(1) != headTotal(2)+(3)+(4)+(5)...

    var total = 1; // Include myself

    _.each(data.senior, function(row) {
      if(row['Reports to Senior Post'] !== id)
        return;

      total += +row['FTE'];

      total += my.headTotals(row['Post Unique Reference']);
    });

    // Also include juniors
    _.each(data.junior, function(row) {
      if(row['Reporting Senior Post'] !== id)
        return;

      total += +row['Number of Posts in FTE'];
    });

    return total;
  }

  function lookup(r, lu) {
    // Rough and ready...


    var total = 1; // Include myself
    
    var id = r['Post Unique Reference'];

    lu[id] = {
      id: id,
      title: r['Job Title'],
      fte: r['FTE'],
      directReports: []
    };

    _.each(data.senior, function(row) {
      if(row['Reports to Senior Post'] !== id)
        return;

      var reportId = row['Post Unique Reference'];

      total += +row['FTE'];

      var headCount = lookup(row, lu);

      total += headCount;

      lu[id].directReports.push({
        id: reportId,
        title: row['Job Title'],
        fte: row['FTE'],
        senior: true,
        headCount: headCount
      });
    });

    // Also include juniors
    _.each(data.junior, function(row) {
      if(row['Reporting Senior Post'] !== id)
        return;

      lu[id].directReports.push({
        title: row['Generic Job Title'],
        fte: row['Number of Posts in FTE'],
        senior: false
      });

      total += +row['Number of Posts in FTE'];
    });

    lu[id].total = total;

    return total;
  }

  my.lookup = function(id) {
    // Return a lookup table rooted on id and keyed on post ref

    var row;
    _.each(data.senior, function(r) {
      if(r['Post Unique Reference'] !== id)
        return;
      row = r;
    });

    // console.log(row);

    var lu = {};
    lookup (row, lu);
    return lu;
  }

  return my;
}());