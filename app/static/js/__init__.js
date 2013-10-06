//all dojo requires
{
dojo.require("dojo.ready");
dojo.require("dojo.dom");
dojo.require("dojo.parser");
dojo.require("dijit.layout.ContentPane");
dojo.require("dijit.layout.BorderContainer");
dojo.require("dojox.layout.ExpandoPane");
dojo.require("dojo.data.ItemFileWriteStore");
dojo.require("dijit.TitlePane");
dojo.require("dijit.form.HorizontalSlider");
dojo.require("dijit.layout.BorderContainer");
dojo.require("dijit.layout.ContentPane");
dojo.require("dijit.layout.TabContainer");
dojo.require("dijit.layout.AccordionContainer");
dojo.require("dojox.grid.DataGrid");
}

//global variables
var map;
var app = {layers:{},
            currentLayer:'',
            geoJsonParser: new OpenLayers.Format.GeoJSON(),
            wktParser: new OpenLayers.Format.WKT()
            };

//Project setup, called on dojo.ready, Create Layers, Panels, Layer Specific Event Listeners
function setupProject(){


    //Accordion pane must be visible to add content panes
    dijit.byId('tabContainer').selectChild('inputsTab');
    var fidWidth = '35px';
    var numWidth = '80px';
    var txtWidth = '100px';

    //Switch Statement on project type. Different layers and table column definitions
    switch(projectProperties.tid)
    {
        case 1:
        //Simplified Sewerage
        var dwellingColumns = [ {dataField:'fid',           displayField:'FID',             width:fidWidth},
                                {dataField:'owner',         displayField:'Owner',           width:txtWidth},
                                {dataField:'occupants',     displayField:'Occupants',       width: numWidth}];
        app.layers['dwelling'] = new MyFeatureLayer(map, 'dwelling','Digitize Dwellings',
            ['POLYGON'],dwellingColumns,"#00E600", projectProperties.publicExample);
        var impedanceColumns = [{dataField:'fid',           displayField:'FID',             width:fidWidth},
                                {dataField:'impedance',     displayField:'Impedance',       width:txtWidth}];
        app.layers['impedance'] = new MyFeatureLayer(map, 'impedance','Identify Barriers',
            ['LINESTRING','POLYGON'],impedanceColumns,"#FFCC00", projectProperties.publicExample);
        var tankColumns =      [{dataField:'fid',           displayField:'FID',             width:fidWidth},
                                {dataField:'description',   displayField:'Tank Site',       width:txtWidth}];
        app.layers['tank'] = new MyFeatureLayer(map, 'tank','Septic Tank Sites',
            ['POLYGON'],tankColumns,"#2EFEF7", projectProperties.publicExample);
        var treatmentColumns =      [{dataField:'fid',           displayField:'FID',             width:fidWidth},
                                     {dataField:'description',   displayField:'Treatment Site',  width:txtWidth}];
        app.layers['treatment'] = new MyFeatureLayer(map, 'treatment','Water Treatment Sites',
            ['POLYGON'],treatmentColumns,"#2EFEF0",projectProperties.publicExample);
      break;
    case 2:
        //Water Supply
        var dwellingColumns = [ {dataField:'fid',           displayField:'FID',             width:fidWidth},
                                {dataField:'owner',         displayField:'Owner',           width:txtWidth},
                                {dataField:'occupants',     displayField:'Occupants',       width:numWidth}];
        app.layers['dwelling'] = new MyFeatureLayer(map, 'dwelling','Digitize Dwellings',
            ['POINT'],dwellingColumns,"#00E600",projectProperties.publicExample);
        var impedanceColumns = [{dataField:'fid',           displayField:'FID',             width:fidWidth},
                                {dataField:'impedance',     displayField:'Impedance'}];
        app.layers['impedance'] = new MyFeatureLayer(map, 'impedance','Identify Barriers',
            ['LINESTRING','POLYGON'],impedanceColumns,"#FFCC00", projectProperties.publicExample);
        var waterColumns =      [{dataField:'fid',           displayField:'FID',             width:fidWidth},
                                {dataField:'description',   displayField:'Description',     width:txtWidth},
                                {dataField:'flow_rate_gpm', displayField:'FlowRate',        width:numWidth}];
        app.layers['water'] = new MyFeatureLayer(map, 'water','Water Sources',
            ['POINT'],waterColumns,"#FF4000", projectProperties.publicExample);
        var tankColumns =      [{dataField:'fid',           displayField:'FID',         width:fidWidth},
                                {dataField:'description',   displayField:'Tank Site',   width:txtWidth}];
        app.layers['tank'] = new MyFeatureLayer(map, 'tank','Water Tank Sites',
            ['POLYGON'],tankColumns,"#2EFEF7", projectProperties.publicExample);
        break;
    default:
        alert('Project Type Not Determined')
    }

    //Add the Generate Design Panel
    {
    var genDesDiv = document.createElement('div');
    var genDesignButton = document.createElement('input');
    genDesignButton.type = 'button';
    genDesignButton.id = 'genDesignButton';
    genDesignButton.value = 'Generate Design';
    genDesignButton.onclick = function(){generateDesign()};
    genDesignButton.style.margins = '35px';
    genDesDiv.appendChild(genDesignButton);
    var designPar = document.createElement('p');
    designPar.innerHTML = 'Generate the design when all inputs are complete. ';
    designPar.innerHTML += 'This will overwrite the results of a previous design. ';
    designPar.innerHTML += 'Features outside project extent will not be included. ';
    designPar.innerHTML += 'Processing may take significant time depending on the size of the project. ';
    designPar.innerHTML += 'You will receive an email at ' + userEmail + ' when the result is available';
    genDesDiv.appendChild(designPar);

    var generateDesignPanel = new dijit.layout.ContentPane({
    id: 'designPanel',
    title: 'Generate Design',
    content: genDesDiv
    });
    dijit.byId('inputsTab').addChild(generateDesignPanel);
    }

    //Reselect the home tab
    dijit.byId('tabContainer').selectChild('homeTab');
}

//Initialize application
dojo.ready(function () {
    //General init statements, renderers, reset radio buttons, num Zoom levels, cache buster, etc.
    {
    var zoomlevels =20;

    document.getElementById('LocSearch').checked = true;
    DDDegMinOnChange();
//    Random numbers for cache buster
    var rand1 = Math.floor(Math.random() * 10000001);
    var rand2 = Math.floor(Math.random() * 10000001);
    }

    //Create the OpenLayers map object
    map = new OpenLayers.Map('map_element',
        {
            allOverlays: false,
            controls: [
                        new OpenLayers.Control.Navigation({dragPanOptions: {enableKinetic: true}}),
                        new OpenLayers.Control.PanZoomBar({}),
                        new OpenLayers.Control.LayerSwitcher({})
                    ],
            projection: new OpenLayers.Projection("EPSG:3857"),
            numZoomLevels: zoomlevels,
            zoom:2
        }
    );

    //Add base layers
    map.addLayers([
        new OpenLayers.Layer.Google("Hybrid",
        { type: google.maps.MapTypeId.HYBRID, numZoomLevels: zoomlevels}),
        new OpenLayers.Layer.Google("Streets",
        { numZoomLevels: zoomlevels }),
        new OpenLayers.Layer.Google("Satellite",
        { type: google.maps.MapTypeId.SATELLITE, numZoomLevels: zoomlevels}),
        new OpenLayers.Layer.Google("Physical",
        { type: google.maps.MapTypeId.TERRAIN, numZoomLevels: zoomlevels }
        )]);

    //Add elevation hillshade layer if it exists
    //addDemHillshade(projectProperties.pid, map);

    //Add the extent layer feature if it exists for the project
    app['extentLayer'] = new ExtentLayer(map, projectProperties, 'set_extent_radio', projectProperties.publicExample);

    //Add layers and dojo panels specific to the project Type, Water Supply or Sewerage
    setupProject(projectProperties.publicExample);

    var getFeaturesURL;
    if (projectProperties.publicExample){
        getFeaturesURL =  $SCRIPT_ROOT + '/map/getexamplefeatures?' + rand1 + '=' + rand2;
    }
    else{
        /*Cache buster, ensures features are loaded from server and not browser cache
        get featuresUrl has random request parameters ex:  ..getfeatures?479223=752453 */
        getFeaturesURL =  $SCRIPT_ROOT + '/map/getfeatures?' + rand1 + '=' + rand2;
    }

    //Get the project features
    $.ajax({
        /*Cache buster, ensures features are loaded from server and not browser cache
        get featuresUrl has random request parameters ex:  ..getfeatures?479223=752453 */
        url: getFeaturesURL,
        type: 'GET',
        data: {},
        success: function (response) {
            var par = JSON.parse(response).features;
            for (var i = 0; i<par.length;i++){
                var layerName = par[i].properties.discriminator.split('_')[0];

                if (app.layers[layerName])
                    app.layers[layerName].loadFeature(par[i],app.geoJsonParser);
                else
                    alert('layer ' + layerName + ' not found')
            }
            //Render all the grids with the loaded features
            for (var key in app.layers)
                app.layers[key].attributeGrid.render();
            //Force Refresh
            map.zoomIn();
            map.zoomOut();

            //Add the vector layer event listeners after loading
            for (var key in app.layers){
                app.layers[key].vectorLayer.events.on({
                    "featureadded": function(feat){app.layers[key].addFeature(feat);},
                    "afterfeaturemodified": function(feat){app.layers[key].modifyFeature(feat);},
                    "featureselected": function(feat){app.layers[key].selectFeature(feat);},
                    "featureunselected": function(feat){app.layers[key].unselectFeature(feat);}
                });
            }
        },
        error: function (xhr, ajaxOptions, thrownError) {
            alert(xhr.status);
            alert(thrownError);
        }
    });
});