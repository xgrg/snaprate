var points = [];
var dragging = false,
  drawing = false,
  startPoint;


function drawPolygon(points, color){
  color = color + '77';
  var g = svg.append('g');
  g.append('polygon')
    .attr('points', points)
    .style('fill', color);
  for (var i = 0; i < points.length; i++) {
    var circle = g.selectAll('circles')
      .data([points[i]])
      .enter()
      .append('circle')
      .attr('cx', points[i][0])
      .attr('cy', points[i][1])
      .attr('r', 4)
      .attr('fill', '#FDBC07')
      .attr('stroke', '#000')
      .attr('is-handle', 'true')
      .style({
        cursor: 'move'
      })
      .call(dragger);
  }
  points.splice(0);
  drawing = false;
}

function addButton(label) {
  c = colors[label];
  polygons = collect_polygons();
  name = '#' + polygons.length;
  html = '<button type="button" class="btn btn-dark" '+
    'data-value="' + label + '" data-index="' + polygons.length +
    '" style="background-color:' + c + '">'+ name + '</button>';
  $(html).insertAfter("#casenumber")
  $('#firstline button.btn.btn-dark').click(function(){
    detailsPolygon($(this));
  });

}

function handleDrag() {
  if (drawing) return;
  var dragCircle = d3.select(this),
    newPoints = [],
    circle;
  dragging = true;
  var poly = d3.select(this.parentNode).select('polygon');
  var circles = d3.select(this.parentNode).selectAll('circle');
  dragCircle
    .attr('cx', d3.event.x)
    .attr('cy', d3.event.y);
  for (var i = 0; i < circles[0].length; i++) {
    circle = d3.select(circles[0][i]);
    newPoints.push([circle.attr('cx'), circle.attr('cy')]);
  }
  poly.attr('points', newPoints);
}

function drawPoly(polygons) {
  html = '';
  for (var j = 0; j < polygons.length ; j++) {
    points = polygons[j]['polygon'];
    label = polygons[j]['label'];
    drawPolygon(points, colors[label]);

    addButton(label);
  }

}

function update_polygons(polygons) {
  $("#firstline button.btn.btn-dark").remove();
  d3.selectAll('g').remove();
  initialize_polygons();
  drawPoly(polygons);

}

function collect_polygons() {
  polygons = $('polygon');
  p = []
  labels = []
  $('#firstline button.btn.btn-dark').each(function(){
    labels.push($(this).attr('data-value'));
  })
  for (var i = 0; i < polygons.length; i++) {
    polygon = []
    for (var j = 0; j < polygons[i].animatedPoints.length; j++) {
      pt = polygons[i].animatedPoints[j]
      polygon.push([pt['x'], pt['y']])

    }
    p.push({'polygon':polygon, 'label': labels[i]});
  }
  return p;
}

function find_point(x, y) {
  min_point = -1
  dist = 1000;
  polygons = $('polygon');
  for (var i = 0; i < polygons.length; i++) {
    for (var j = 0; j < polygons[i].animatedPoints.length; j++) {
      pt = polygons[i].animatedPoints[j]
      a = pt['x'] - x;
      b = pt['y'] - y;
      var c = Math.sqrt(a * a + b * b);
      if (c < dist) {
        dist = c
        min_index = [pt, i, j];
      }
    }
  }
  return min_index;
}

function initialize_polygons() {
  svg = d3.select('svg');

  points = [];

  svg.on('mouseup', function() {
    console.log('dragging:', dragging, 'drawing:', drawing)
    if (dragging)
      return;

    if (d3.event.target.hasAttribute('is-handle')) {
      if (!drawing) {
        if (d3.event.shiftKey) {
          res = find_point(d3.mouse(this)[0], d3.mouse(this)[1]);
          console.log(res)
          polygons = collect_polygons();

          if (polygons[res[1]]['polygon'].length > 3)
            polygons[res[1]]['polygon'].splice(res[2], 1);
          update_polygons(polygons);
        }
        else if (d3.event.ctrlKey){
          polygons = collect_polygons();
          res = find_point(d3.mouse(this)[0], d3.mouse(this)[1]);
          console.log(res)
          polygons = collect_polygons();
          if (res[2] > 0)
            next_vtx = polygons[res[1]]['polygon'][res[2]-1];
          else
            next_vtx = polygons[res[1]]['polygon'][polygons[res[1]]['polygon'].length - 1];
          x = (res[0]['x'] + next_vtx[0])/2.0
          y = (res[0]['y'] + next_vtx[1])/2.0
          polygons[res[1]]['polygon'].splice(res[2], 0, [x,y])
          update_polygons(polygons);
        }
      }
      if (points.length > 2){
        default_label = 0
        c = colors[default_label];
        svg.select('g.drawPoly').remove();
        drawPolygon(points, c);
        addButton(default_label);
      }
      return;

    };
    drawing = true;
    startPoint = [d3.mouse(this)[0], d3.mouse(this)[1]];
    if (svg.select('g.drawPoly').empty()) g = svg.append('g').attr('class', 'drawPoly');

    points.push(d3.mouse(this));

    g.select('polyline').remove();
    var polyline = g.append('polyline').attr('points', points)
      .style('fill', 'none')
      .attr('stroke', '#000');

    for (var i = 0; i < points.length; i++) {
      g.append('circle')
        .attr('cx', points[i][0])
        .attr('cy', points[i][1])
        .attr('r', 4)
        .attr('fill', 'yellow')
        .attr('stroke', '#000')
        .attr('is-handle', 'true')
        .style({
          cursor: 'pointer'
        });
    }
  });

  svg.on('mousemove', function() {
    if (!drawing) return;
    var g = d3.select('g.drawPoly');
    g.select('line').remove();
    var line = g.append('line')
      .attr('x1', startPoint[0])
      .attr('y1', startPoint[1])
      .attr('x2', d3.mouse(this)[0] + 2)
      .attr('y2', d3.mouse(this)[1])
      .attr('stroke', '#53DBF3')
      .attr('stroke-width', 1);
  })

  dragger = d3.behavior.drag()
    .on('drag', handleDrag)
    .on('dragend', function(d) {
      dragging = false;
    });

}
