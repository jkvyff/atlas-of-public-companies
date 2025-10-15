var SearchableMapLib = SearchableMapLib || {};
var SearchableMapLib = {

  // parameters to be defined on initialize() 
  map_centroid: [],
  defaultZoom: 9,
  filePath: '',
  fileType: '',
  csvOptions: '',
  listOrderBy: '',
  recordName: '',
  recordNamePlural: '',
  useMarkerClustering: false,
  debug: false,

  // internal properties
  radius: '',
  csvData: null,
  geojsonData: null,
  currentResults: null,
  currentResultsLayer: null,
  currentPinpoint: null,
  lastClickedLayer: null,

  initialize: function(options){
    options = options || {};

    SearchableMapLib.map_centroid = options.map_centroid || [41.881832, -87.623177],
    SearchableMapLib.defaultZoom = options.defaultZoom || 9,
    SearchableMapLib.filePath = options.filePath || "",
    SearchableMapLib.fileType = options.fileType || "csv",
    SearchableMapLib.csvOptions = options.csvOptions || {separator: ',', delimiter: '"'},
    SearchableMapLib.listOrderBy = options.listOrderBy || "",
    SearchableMapLib.recordName = options.recordName || "result",
    SearchableMapLib.recordNamePlural = options.recordNamePlural || "results",
    SearchableMapLib.radius = options.defaultRadius || 805,
    SearchableMapLib.useMarkerClustering = options.useMarkerClustering || false,
    SearchableMapLib.debug = options.debug || false

    if (SearchableMapLib.debug)
      console.log('debug mode is on');

    //reset filters
    $("#search-address").val(SearchableMapLib.convertToPlainString($.address.parameter('address')));

    var loadRadius = SearchableMapLib.convertToPlainString($.address.parameter('radius'));
    if (loadRadius != "") 
        $("#search-radius").val(loadRadius);
    else 
        $("#search-radius").val(SearchableMapLib.radius);

    $(":checkbox").prop("checked", "checked");

    // No need for Google geocoder - we'll use Nominatim (OpenStreetMap)
    // initiate leaflet map
    if (!SearchableMapLib.map) {
      SearchableMapLib.map = new L.Map('mapCanvas', {
        center: SearchableMapLib.map_centroid,
        zoom: SearchableMapLib.defaultZoom,
        scrollWheelZoom: false
      });

      // Use OpenStreetMap instead of Google Maps
      var osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
      });

      SearchableMapLib.map.addLayer(osmLayer);

      //add hover info control
      SearchableMapLib.info = L.control({position: 'bottomleft'});

      SearchableMapLib.info.onAdd = function (map) {
          this._div = L.DomUtil.create('div', 'info'); // create a div with a class "info"
          this.update();
          return this._div;
      };

      // method that we will use to update the control based on feature properties passed
      var hover_template;
      $.get( "../templates/hover.ejs", function( template ) {
        hover_template = template;
      });
      SearchableMapLib.info.update = function (props) {
        if (props) {
          this._div.innerHTML = ejs.render(hover_template, {obj: props});
        }
        else {
          this._div.innerHTML = 'Hover over a ' + SearchableMapLib.recordName;
        }
      };

      SearchableMapLib.info.clear = function(){
        this._div.innerHTML = 'Hover over a ' + SearchableMapLib.recordName;
      };

      //add results control
      SearchableMapLib.results_div = L.control({position: 'topright'});

      SearchableMapLib.results_div.onAdd = function (map) {
        this._div = L.DomUtil.create('div', 'results-count');
        this._div.innerHTML = "";
        return this._div;
      };

      SearchableMapLib.results_div.update = function (count){
        var recname = SearchableMapLib.recordNamePlural;
        if (count == 1) {
            recname = SearchableMapLib.recordName;
        }

        this._div.innerHTML = count.toLocaleString('en') + ' ' + recname + ' found';
      };

      SearchableMapLib.results_div.addTo(SearchableMapLib.map);
      SearchableMapLib.info.addTo(SearchableMapLib.map);

      $.when($.get(SearchableMapLib.filePath)).then(
      function (data) {

        if (SearchableMapLib.fileType == 'geojson') {
          if (SearchableMapLib.debug) console.log('loading geojson');
          // sometimes the server returns the file as text and we have to parse it
          if (typeof data == 'string')
            SearchableMapLib.geojsonData = JSON.parse(data);
          else
            SearchableMapLib.geojsonData = data
        }
        else if (SearchableMapLib.fileType == 'csv' ){
          // convert CSV
          if (SearchableMapLib.debug) console.log('converting to csv');
          SearchableMapLib.geojsonData = convertCsvToGeojson(data)
        }
        else {
          // error!
          console.log ("fileType must be 'csv' or 'geojson'")
        }

        if (SearchableMapLib.debug) {
          console.log('data loaded:');
          console.log(SearchableMapLib.geojsonData);
        }

        // Populate sector dropdown with unique sectors
        SearchableMapLib.populateSectorDropdown();

        SearchableMapLib.doSearch();

      });
    }
  },

  doSearch: function() {
    SearchableMapLib.clearSearch();
    var address = $("#search-address").val();
    SearchableMapLib.radius = $("#search-radius").val();

    if (SearchableMapLib.radius == null && address != "") {
      SearchableMapLib.radius = 805;
    }

    if (address != "") {
      // Use Nominatim (OpenStreetMap) geocoding instead of Google
      $.getJSON('https://nominatim.openstreetmap.org/search', {
        q: address,
        format: 'json',
        limit: 1
      }, function(results) {
        if (results && results.length > 0) {
          SearchableMapLib.currentPinpoint = [parseFloat(results[0].lat), parseFloat(results[0].lon)];
          $.address.parameter('address', encodeURIComponent(address));
          $.address.parameter('radius', SearchableMapLib.radius);
          SearchableMapLib.address = address;
          SearchableMapLib.createSQL(); // Must call create SQL before setting parameters.
          SearchableMapLib.setZoom();
          SearchableMapLib.addIcon();
          SearchableMapLib.addCircle();
          SearchableMapLib.renderMap();
          SearchableMapLib.renderList();
          SearchableMapLib.getResults();
        }
        else {
          alert("We could not find your address. Please try a different search.");
        }
      }).fail(function() {
        alert("Geocoding service is unavailable. Please try again later.");
      });
    }
    else { //search without geocoding callback
      SearchableMapLib.map.setView(new L.LatLng( SearchableMapLib.map_centroid[0], SearchableMapLib.map_centroid[1] ), SearchableMapLib.defaultZoom)
      SearchableMapLib.createSQL(); // Must call create SQL before setting parameters.
      SearchableMapLib.renderMap();
      SearchableMapLib.renderList();
      SearchableMapLib.getResults();
    }

  },

  renderMap: function() {
    SearchableMapLib.currentResultsLayer.addTo(SearchableMapLib.map);
  },

  renderList: function() {
    var results = $('#results-list');
    results.empty();

    if (SearchableMapLib.currentResults.features.length == 0) {
      results.append("<p class='no-results'>No results. Please broaden your search.</p>");
    }
    else {
      var row_content;
      $.get( "../templates/table-row.ejs", function( template ) {
          for (idx in SearchableMapLib.currentResults.features) {
            row_content = ejs.render(template, {obj: SearchableMapLib.currentResults.features[idx].properties});

            results.append(row_content);
          }
        });
      }
  },

  getResults: function() {
    if (SearchableMapLib.debug) {
      console.log('results length')
      console.log(SearchableMapLib.currentResults.features.length)
    }

    var recname = SearchableMapLib.recordNamePlural;
    if (SearchableMapLib.currentResults.features.length == 1) {
        recname = SearchableMapLib.recordName;
    }

    SearchableMapLib.results_div.update(SearchableMapLib.currentResults.features.length);

    $('#list-result-count').html(SearchableMapLib.currentResults.features.length.toLocaleString('en') + ' ' + recname + ' found')
    
    // Update the blue box with the count
    $('#results-number').html(SearchableMapLib.currentResults.features.length.toLocaleString('en') + ' public ' + recname + ' found');
  },

  modalPop: function(data) {
    if (SearchableMapLib.debug) {
      console.log('launch modal')
      console.log(data);
    }
    var modal_content;
    $.get( "../templates/popup.ejs", function( template ) {
        modal_content = ejs.render(template, {obj: data});
        $('#modal-pop').modal();
        $('#modal-main').html(modal_content);
    });
  },

  clearSearch: function(){
    if (SearchableMapLib.currentResultsLayer) {
      SearchableMapLib.currentResultsLayer.remove();
    }
    if (SearchableMapLib.centerMark)
      SearchableMapLib.map.removeLayer( SearchableMapLib.centerMark );
    if (SearchableMapLib.radiusCircle)
      SearchableMapLib.map.removeLayer( SearchableMapLib.radiusCircle );
  },

  createSQL: function() {
    var address = $("#search-address").val();

    // this is a fun hack to do a deep copy of the GeoJSON data
    SearchableMapLib.currentResults = JSON.parse(JSON.stringify(SearchableMapLib.geojsonData));

    if(SearchableMapLib.currentPinpoint != null && address != '') {
        var point = turf.point([SearchableMapLib.currentPinpoint[1], SearchableMapLib.currentPinpoint[0]]);
        var buffered = turf.buffer(point, SearchableMapLib.radius, {units: 'meters'});

        SearchableMapLib.currentResults = turf.pointsWithinPolygon(SearchableMapLib.currentResults, buffered);

        if (SearchableMapLib.debug) {
          console.log('found points within')
          console.log(SearchableMapLib.currentResults);
        }
    }

    //-----custom filters-----

    //-----name search filter-----
    var name_search = $("#search-name").val().replace("'", "\'");
    if (name_search != '') {
      SearchableMapLib.currentResults.features = $.grep(SearchableMapLib.currentResults.features, function(r) {
          var companyName = r.properties["Company Name"] || r.properties["company_name"] || "";
          return companyName.toLowerCase().indexOf(name_search.toLowerCase()) > -1;
        });
    }
    //-----end name search filter-----

    //-----sector filter-----
    var sector_filter = $("#search-sector").val();
    if (sector_filter != '') {
      SearchableMapLib.currentResults.features = $.grep(SearchableMapLib.currentResults.features, function(r) {
          var sector = r.properties["Sector"] || "";
          return sector === sector_filter;
        });
    }
    //-----end sector filter-----

    // -----end of custom filters-----

    var geojsonLayer = L.geoJSON(SearchableMapLib.currentResults, {
        pointToLayer: function (feature, latlng) {
          return L.marker(latlng, {icon: SearchableMapLib.getIcon(feature.properties["Sector"])} );
        },
        onEachFeature: onEachFeature
      }
    );

    // Use marker clustering if enabled
    if (SearchableMapLib.useMarkerClustering) {
      SearchableMapLib.currentResultsLayer = L.markerClusterGroup({
        showCoverageOnHover: false,
        maxClusterRadius: 25
      });
      SearchableMapLib.currentResultsLayer.addLayer(geojsonLayer);
    } else {
      SearchableMapLib.currentResultsLayer = geojsonLayer;
    }

    //messy - clean this up later
    function onEachFeature(feature, layer) {
      layer.on({
        mouseover: hoverFeature,
        mouseout: removeHover,
        click: modalPop
      });
    }

    function hoverFeature(e) {
      SearchableMapLib.info.update(e.target.feature.properties);
    }

    function removeHover(e) {
      SearchableMapLib.info.update();
    }

    function modalPop(e) {
      SearchableMapLib.modalPop(e.target.feature.properties)
    }

  },

  setZoom: function() {
    var zoom = '';
    if (SearchableMapLib.radius >= 1610000) zoom = 4; // 1000 miles
    else if (SearchableMapLib.radius >= 805000) zoom = 5; // 500 miles
    else if (SearchableMapLib.radius >= 402500) zoom = 6; // 250 miles
    else if (SearchableMapLib.radius >= 161000) zoom = 7; // 100 miles
    else if (SearchableMapLib.radius >= 80500) zoom = 8; // 50 miles
    else if (SearchableMapLib.radius >= 40250) zoom = 9; // 25 miles
    else if (SearchableMapLib.radius >= 16100) zoom = 11; // 10 miles
    else if (SearchableMapLib.radius >= 8050) zoom = 12; // 5 miles
    else if (SearchableMapLib.radius >= 3220) zoom = 13; // 2 miles
    else if (SearchableMapLib.radius >= 1610) zoom = 14; // 1 mile
    else if (SearchableMapLib.radius >= 805) zoom = 15; // 1/2 mile
    else if (SearchableMapLib.radius >= 400) zoom = 16; // 1/4 mile
    else zoom = 16;

    SearchableMapLib.map.setView(new L.LatLng( SearchableMapLib.currentPinpoint[0], SearchableMapLib.currentPinpoint[1] ), zoom)
  },

  addIcon: function() {
    SearchableMapLib.centerMark = new L.Marker(SearchableMapLib.currentPinpoint, { icon: (new L.Icon({
            iconUrl: '/img/blue-pushpin.png',
            iconSize: [32, 32],
            iconAnchor: [10, 32]
    }))});

    SearchableMapLib.centerMark.addTo(SearchableMapLib.map);
  },

  addCircle: function() {
    SearchableMapLib.radiusCircle = L.circle(SearchableMapLib.currentPinpoint, {
        radius: SearchableMapLib.radius,
        fillColor:'#1d5492',
        fillOpacity:'0.1',
        stroke: false,
        clickable: false
    });

    SearchableMapLib.radiusCircle.addTo(SearchableMapLib.map);
  },

  //converts a slug or query string in to readable text
  convertToPlainString: function(text) {
    if (text == undefined) return '';
    return decodeURIComponent(text);
  },

  // -----custom functions-----
  populateSectorDropdown: function() {
    // Define sectors based on the color coding in getIcon
    var sectors = [
      'Communication Services',
      'Consumer Discretionary',
      'Consumer Staples',
      'Energy',
      'Financials',
      'Health Care',
      'Industrials',
      'Information Technology',
      'Materials',
      'Real Estate',
      'Utilities'
    ];
    
    // Populate the dropdown
    var dropdown = $('#search-sector');
    sectors.forEach(function(sector) {
      dropdown.append($('<option></option>').attr('value', sector).text(sector));
    });
  },

  getIcon: function(sector){
    if (!sector) return greyIcon;
    
    // Map sectors to colors based on the legend
    if (sector.toLowerCase().includes("health")) return blueIcon;
    if (sector.toLowerCase().includes("technology") || sector.toLowerCase().includes("communication")) return violetIcon;
    if (sector.toLowerCase().includes("financial")) return greenIcon;
    if (sector.toLowerCase().includes("energy")) return orangeIcon;
    if (sector.toLowerCase().includes("material")) return greyIcon;
    if (sector.toLowerCase().includes("industrial") || sector.toLowerCase().includes("utilities")) return blackIcon;
    if (sector.toLowerCase().includes("consumer")) return yellowIcon;
    if (sector.toLowerCase().includes("real estate")) return redIcon;
    
    // Default to grey for unknown sectors
    return greyIcon;
  },
  // -----end custom functions-----

}
