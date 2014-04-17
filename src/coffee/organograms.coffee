window.viz ?= {}

viz.shallowCopy = (object) ->
  out = {}
  for k,v of object
    out[k] = v
  return out

viz.trim = (x,maxlen) ->
  if (maxlen>=0) and (x.length>maxlen)
    return x.substr(0,maxlen) + '...'
  return x

viz.money_to_string = (amount) ->
  out = ''
  amount = String(amount)
  while amount.length>3
    out = ',' + amount.substring(amount.length-3) + out
    amount = amount.substring(0,amount.length-3)
  return amount + out

d3.selection.prototype.moveToBack = ->
    @each ->
        firstChild = @parentNode.firstChild
        if (firstChild) then @parentNode.insertBefore(this, firstChild)

# =====================================

d3.json "data/csv/index.json", (index)->
  select = d3.select('select#index')
  select.attr('disabled',null).classed('disabled',false)
  select.selectAll('option').text('Select a department...')
  options = select.selectAll('option')
    .data(index)
    .enter()
    .append('option')
    .text((d)->d.name)
    .attr('value',(d)-> d.value)
  # Go go gadget jQuery
  $('select#index')
    .chosen()
    .on 'change', (e)->
      val  = $(e.delegateTarget).val()
      text = $(e.delegateTarget).find("option[value=\"#{val}\"]").text()
      viz.setActiveOrganogram(val,text)
      d3.select('#organogram-title').text("Loading...")
      d3.select('#organogram-viz').html('')
  # -- preload
  indexNames = index.map (x)->x.name
  hash = window.location.hash.substr(1)
  hashIndex = indexNames.indexOf(hash)
  if hashIndex<0
    hashIndex = 1
  viz.setActiveOrganogram index[hashIndex].value,index[hashIndex].name
  $("select#index").val(index[hashIndex].value).trigger("chosen:updated")


viz.setActiveOrganogram = (slug,title) ->
  window.location.hash = title
  viz.activeOrganogram =
    junior: null
    senior: null
    slug  : slug
    title : title
  d3.csv "data/csv/#{slug}-senior.csv", (senior) ->
    if (viz.activeOrganogram.slug==slug)
      viz.activeOrganogram.senior = senior
      viz.renderActiveOrganogram()
  d3.csv "data/csv/#{slug}-junior.csv", (junior) ->
    if (viz.activeOrganogram.slug==slug)
      viz.activeOrganogram.junior = junior
      viz.renderActiveOrganogram()


viz.renderActiveOrganogram = ->
  senior = viz.activeOrganogram.senior
  junior = viz.activeOrganogram.junior
  if not (senior and junior) then return
  d3.select("#organogram-title").text("Viewing: "+viz.activeOrganogram.title)
  root = null
  lookup = {}
  for row in senior
    lookup[ row['Post Unique Reference'] ] = row
    row['children'] = []
  for row in senior
    parent = row['Reports to Senior Post']
    row.senior = true
    row.name   = row['Job Title'] or '(unknown)'
    row.value  = row['Actual Pay Floor (£)']
    if parent.toLowerCase()=='xx' 
      root = row
    else
      lookup[parent]['children'].push row
  for row in junior
    row.senior = false
    row.name   = row['Generic Job Title'] or '(unknown)'
    row.value  = row['Payscale Minimum (£)']
    parent = row['Reporting Senior Post']
    lookup[parent]['children'].push row
  new viz.organogram(root)

class window.viz.organogram
  width: 940
  height: 800
  radius: 270
  pw: 130
  ph: 14
  # OrgChart: Redistribute y values to cluser around the core
  offset: (y) => (y*y)/@radius 
  color: d3.scale.category20c()

  constructor: (raw_root)->
    @orgChart = @buildOrgChart(raw_root,'','root')
    @treeMap = @buildTreeMap(@orgChart)
    @container = d3.select('#organogram-viz')
    @svg = d3.select('#organogram-viz')
      .append('svg')
      .attr('width',@width)
      .attr('height',@height)
      .append('g')
      .attr('transform',"translate(#{@width/2},#{@height/2})")
    @defs = @svg.append('defs')
    # Initial state
    if (d3.select('.organogram-button:checked').attr('value')=='option2')
      @renderTreeMap(intro=true)
    else
      @renderOrgChart(intro=true)
    # Bind interactive elements
    btnz = d3.selectAll('.organogram-button')
    btnz.on 'click',(_x,index)=>
      btnz.classed('active',(_x,i)->i==index)
      if index==0 then @renderOrgChart() else @renderTreeMap()
    @hoverBox = @container.append('div')
      .classed('hoverbox',true)

  # Recursive function
  buildOrgChart: (d, parentId, myId) =>
    out = {
      original : d
      name     : d.name
      value    : d.value
      key      : myId
      group    : parentId
      isLeaf   : true
    }
    if (d.children and d.children.length) 
      out.isLeaf   = false
      out.group    = myId
      out.children = ( @buildOrgChart(child,myId,"#{myId}.#{i}") for child,i in d.children )
    return out

  # Bizarre behaviour of the D3 Treemap engine means
  # I have to create a shallow copy of the entire tree
  # with a /subtly/ different structure...!
  buildTreeMap: (d) =>
    if not d.children then return d
    out =
      key: "tmp-#{d.key}"
      children: []
    myself = viz.shallowCopy d
    myself.children = undefined
    out.children.push myself
    for child in d.children
      out.children.push @buildTreeMap(child)
    return out

  hoverPerson: =>
    parent = this
    return (d,i) ->
      window.clearTimeout window.viz.organogram_hover_timeout
      if parent.hovering == d.original
        return
      parent.hovering = d.original
      w     = 280
      space = 20
      bbox        = @.getBoundingClientRect()
      bbox_parent = parent.container[0][0].getBoundingClientRect()
      if (bbox.left-bbox_parent.left+bbox.width/2) > (bbox_parent.width/2)
        left = bbox.left - bbox_parent.left - w - space
      else
        left = bbox.left - bbox_parent.left + bbox.width + space
      left = Math.max(0,Math.min(bbox_parent.width-w,left))
      top = bbox.top - bbox_parent.top + bbox.height/2 - (if d.original.senior then 100 else 50)
      top = Math.max(-50,Math.min(bbox_parent.height-100,top))
      parent.hoverBox.style(
        display:'block'
        left:Math.round(left)+'px'
        top:Math.round(top)+'px'
      )
      #email_link = (x) -> if '@' not in x then x else "<a href=\"mailto:#{x}\">#{x}</a>"
      email_link = (x) -> x
      if d.original.senior
        parent.hoverBox.html "
          <table class=\"table table-bordered table-condensed\">
            <tr><td>Job&nbsp;Title</td><td>#{d.original['Job Title']}</td></tr>
            <tr><td>Unit</td><td>#{d.original['Unit']}</td></tr>
            <tr><td>Profession</td><td>#{d.original['Professional/Occupational Group']}</td></tr>
            <tr><td>Salary</td><td>£#{viz.money_to_string(d.original['Actual Pay Floor (£)'])} - £#{viz.money_to_string(d.original['Actual Pay Ceiling (£)'])}</td></tr>
            <tr><td>Type</td><td><em>Senior Civil Servant</em></td></tr>
            <tr><td colspan=\"2\" style=\"text-align: left;font-weight:normal;font-style:italic;\">#{d.original['Job/Team Function']}</td></tr>
            <tr><td>Name</td><td>#{d.original['Name']}</td></tr>
            <tr><td>Grade</td><td>#{d.original['Grade']}</td></tr>
            <tr><td>#&nbsp;Roles</td><td>#{d.original['FTE']} (full-time equivalent)</td></tr>
            <tr><td>Phone</td><td>#{d.original['Contact Phone']}</td></tr>
            <tr><td>Email</td><td>#{email_link(d.original['Contact E-mail'])}</td></tr>
          </table>"
      else
        parent.hoverBox.html "
          <table class=\"table table-bordered table-condensed\">
            <tr><td>Job&nbsp;Title</td><td>#{d.original['Generic Job Title']}</td></tr>
            <tr><td>Unit</td><td>#{d.original['Unit']}</td></tr>
            <tr><td>Profession</td><td>#{d.original['Professional/Occupational Group']}</td></tr>
            <tr><td>Salary</td><td>£#{viz.money_to_string(d.original['Payscale Minimum (£)'])} - £#{viz.money_to_string(d.original['Payscale Maximum (£)'])}</td></tr>
            <tr><td>Type</td><td><em>Junior Civil Servant</em></td></tr>
            <tr><td>Grade</td><td>#{d.original['Grade']}</td></tr>
            <tr><td>#&nbsp;Roles</td><td>#{d.original['Number of Posts in FTE']} (full-time equivalent)</td></tr>
          </table>"

  hoverPersonOut: (d,i) =>
    window.clearTimeout window.viz.organogram_hover_timeout
    @hovering = null
    window.viz.organogram_hover_timeout = window.setTimeout (=>@hoverBox.style('display','none')), 300

  linkPath: (d) =>
    # Lines between boxes
    @linkline ?= d3.svg.line().interpolate('basis')
    sx = (d.source.x-90) * Math.PI / 180
    sy = @offset(d.source.y)
    tx = (d.target.x-90) * Math.PI / 180
    ty = @offset(d.target.y)
    # Lots of aesthetic tweaks...
    if sy==0 then sx = tx    # Align angles or the central node
    point = (angle,offset) -> [ Math.cos(angle)*offset, Math.sin(angle)*offset ]
    return @linkline [
      point(sx,sy),
      point(sx,sy+80),
      point(tx,ty-40),
      point(tx,ty)
    ]

  setData: (persons,links) =>
    clippath_selection = @defs.selectAll('.clipRect')
      .data(persons, key = (d)->d.key)
    clippath_selection.exit().remove()
    clippath_selection.enter().append('clipPath')
      .classed('clipRect',true)
      .attr('id',(d)->d.key)
      .append('rect')
      .attr('width',@pw)
      .attr('height',@ph)
    # -- Links
    link_selection = @svg.selectAll(".link")
      .data(links,key=(d)->d.target.key)
    link_selection.exit().transition().duration(500).style('opacity',0).remove()
    link_selection.enter().append("path")
      .classed("link", true)
      .attr('fill','none')
      .attr('stroke','rgba(0,0,0,0.2)')
      .attr("d", @linkPath)
      .style('opacity',0)
      .moveToBack()
    # -- Persons
    bgcol = (d) =>
      out = d3.rgb( @color d.group )
      if d.isLeaf then out else out.darker(0.6)
    invertText = (d) -> d3.hsl(bgcol(d)).l < 0.7
    person_selection = @svg.selectAll('.person')
      .data(persons, key=(d)->d.key)
    person_selection.exit().remove()
    g_enter = person_selection.enter().append('g')
      .classed('person',true)
      .attr('clip-path',(d)->"url(##{d.key})")
      #.style('opacity',0)
    g_enter.append('rect')
      .style('display', (d)-> if d.name then 'inline' else 'none')
      .attr('fill',bgcol)
      .on('mouseover',@hoverPerson())
      .on('mouseout',@hoverPersonOut)
    g_enter.append('text')
      .style('display', (d)-> if d.name then 'inline' else 'none')
      .classed('invertText',invertText)
      .attr('dx','2px')
      .attr('dy','1.2em')
      .style('font-size','9px')
      .text((d)->d.name)
    g_enter.append('text')
      .style('display', (d)->if d.name then 'inline' else 'none')
      .classed('invertText',invertText)
      .attr('dx','2px')
      .attr('dy','2.4em')
      .style('font-size','9px')
      .text( (d) -> if not d.name then null else '£'+viz.money_to_string(d.value))

  renderOrgChart: (intro=false) =>
    orgLayout = d3.layout.cluster().size([360,@radius])
    nodes = orgLayout.nodes(@orgChart)
    ripple = (d,i) =>
      i = nodes.length-i
      return i*14
    duration = 500
    if intro
      duration = 0
      ripple = -> 0
    @setData nodes, orgLayout.links(nodes)
    @svg.selectAll(".link").transition()
      .transition()
      .duration(duration*5)
      .delay(if intro then 0 else 1000)
      .style('opacity',1)
    @svg.selectAll('.person')
      .attr('display','inline')
      .transition()
      .duration(duration)
      .delay(ripple)
      .attr('transform', (d) =>
        if d.y==0 then  return "translate(#{-@pw/2},#{-@ph/2})"
        if d.x<180 then return "translate(0,#{-@ph/2})rotate(#{d.x-90},0,#{@ph/2})translate(#{@offset(d.y)})"
        else            return "translate(0,#{-@ph/2})rotate(#{d.x-270},0,#{@ph/2})translate(#{-@offset(d.y)-@pw})"
      )
    @svg.selectAll('.person').select('rect')
      .transition()
      .duration(duration)
      .delay(ripple)
      .attr('width',@pw)
      .attr('height',@ph)
    @svg.selectAll('.clipRect').select('rect').transition()
      .duration(duration)
      .delay(ripple)
      .attr('width',@pw)
      .attr('height',@ph)

  renderTreeMap: (intro=false) =>
    treemap = d3.layout.treemap()
      .size([@width,@height])
      .sticky(true)
      .value( (d) -> d.value )
    nodes = treemap.nodes(@treeMap)
    groups = []
    for node in nodes
      if groups.indexOf(node.group) < 0 then groups.push node.group
    @setData nodes, []
    # --
    duration = 500
    ripple  = (d,i) =>
      return i*14
      index = groups.indexOf(d.group)
      return (index%(groups.length)) * 260
    if intro
      duration = 0
      ripple = -> 0
    # --
    @svg.selectAll('.person')
      .attr('display',(d)->if d.value then 'inline' else 'none')
      .transition()
      .duration(duration)
      .delay(ripple)
      .attr('transform',(d)=>"translate(#{d.x-@width/2},#{d.y-@height/2})")
    @svg.selectAll('.person').select('rect').transition()
      .duration(duration)
      .delay(ripple)
      .attr('width',(d)->d.dx)
      .attr('height',(d)->d.dy)
    @svg.selectAll('.clipRect').select('rect').transition()
      .duration(duration)
      .delay(ripple)
      .attr('width',(d)->Math.max(0,d.dx-1))
      .attr('height',(d)->Math.max(0,d.dy-1))
