function MyFeatureLayer (olMap, myFeatureLayerName,panelTitle,drawTypeArray,dataColumns,color) {
    this.myFeatureLayerName = myFeatureLayerName;
    //GeoJSON object with the features in this layerf
    this.geojson = {type:"FeatureCollection",
                     features: []
    };

    //Define the layer style and layer
    var vector_style = new OpenLayers.Style({
        'fillColor': color,
        'fillOpacity': .2,
        'strokeColor': color,
        'strokeOpacity': .8,
        'strokeWidth': 2,
        'pointRadius': 5
    });

    var vector_style_select = new OpenLayers.Style({
        'fillColor': color,
        'fillOpacity': .5,
        'strokeColor': '#FF00BF',
        'strokeOpacity': 1,
        'strokeWidth': 2,
        'pointRadius': 5
    });

    var vector_style_map = new OpenLayers.StyleMap({
        'default': vector_style,
        'select': vector_style_select
    });

    this.vectorLayer = new OpenLayers.Layer.Vector(myFeatureLayerName, {
        'styleMap': vector_style_map,
        'renderers': app.renderer
    });

    var thisVectorLayer = this.vectorLayer;

    olMap.addLayer(thisVectorLayer);

//    Add Select Control
    this.selectControl = new OpenLayers.Control.SelectFeature(thisVectorLayer);
    this.selectControl.allSelection = true;
    var thisSelectControl = this.selectControl;

    olMap.addControl(thisSelectControl);

    //All Draw controls are initialized, only those relevant to this layer will be loaded
    this.drawControls = {
        'DONE':{activate:function(){},deactivate:function(){}},
        'POINT': new OpenLayers.Control.DrawFeature(this.vectorLayer, OpenLayers.Handler.Point),
        'LINESTRING': new OpenLayers.Control.DrawFeature(this.vectorLayer, OpenLayers.Handler.Path),
        'POLYGON': new OpenLayers.Control.DrawFeature(this.vectorLayer, OpenLayers.Handler.Polygon),
        'MODIFY': new OpenLayers.Control.ModifyFeature(this.vectorLayer)
    };

    olMap.addControls([this.drawControls.POINT,this.drawControls.LINESTRING,
        this.drawControls.POLYGON,this.drawControls.MODIFY]);

    //Add Done and MODIFY to the array of geometry types for this layer
    //Used the activate layer specific drawing tools
    drawTypeArray.splice(0, 0, 'DONE');
    drawTypeArray.push('MODIFY');

    //Configure the element that will be added to the content pane
    var newEl = document.createElement('div');
    newEl.id = myFeatureLayerName + '_editor';
//    newEl.style.overflow = 'auto';
    for (var i = 0; i<drawTypeArray.length;i++){
        var newRadioButton = document.createElement('input');
        newRadioButton.type ='radio';
        newRadioButton.name = myFeatureLayerName + '_inputRadio';
        newRadioButton.id = myFeatureLayerName + '_' + drawTypeArray[i];
        newRadioButton.style.display = 'none';
        //this doesn't fire on programmatic change
        newRadioButton.onchange = function(){
            //'this' refers to the clicked radio button
            var thisId = this.id;
            var layerRadioButtons = document.getElementsByName(this.name);

            for (var i=0;i<layerRadioButtons.length;i++){
                //Get the radiobutton id
                var radioId = layerRadioButtons[i].id;
                //get a reference to the layer and the controls
                var layerName = radioId.split('_')[0];
                var drawControlType = radioId.split('_')[1];
                //Get the image element
                var theImg = document.getElementById(radioId + '_imgLabel');
                //Get the image element src
                var theImgSrc = theImg.src;
                if (thisId==radioId){
                    //this is the control to activate
                    //Use the 'activated' image
                    theImg.src = theImgSrc.replace('_off','_on');
                    app.layers[layerName].drawControls[drawControlType].activate();
                }
                else{
                    //use the 'deactivated' image
                    theImg.src = theImgSrc.replace('_on','_off');
                    app.layers[layerName].drawControls[drawControlType].deactivate();
                }
                app.layers[layerName].selectControl.unselectAll();
            }
        };

        var radLabel = document.createElement('label');
        radLabel.id = myFeatureLayerName + '_' + drawTypeArray[i] + '_label';
        radLabel.htmlFor = myFeatureLayerName + '_' + drawTypeArray[i];
        var imgLabel = document.createElement('img');
        imgLabel.id = myFeatureLayerName + '_' + drawTypeArray[i] + '_imgLabel';
        imgLabel.style.margin = '3px';
        if (i==0){
            //Special init for 'DONE'
            newRadioButton.checked = 'checked';
            imgLabel.src = imgURL + 'icons/' + drawTypeArray[i] + '_on.png';
            imgLabel.alt = drawTypeArray[i]  + '_on';
            imgLabel.title = 'Deactivate draw controls';
        }
        else
        {
            imgLabel.src = imgURL + 'icons/' + drawTypeArray[i] + '_off.png';
            imgLabel.alt = drawTypeArray[i]  + '_off';
            if (drawTypeArray[i] == 'MODIFY')
                imgLabel.title = 'Modify ' + myFeatureLayerName + ' feature';
            else
                imgLabel.title = 'Create ' + myFeatureLayerName + ' feature';
        }
        radLabel.appendChild(imgLabel);
        newEl.appendChild(radLabel);
        newEl.appendChild(newRadioButton);
    }

    var doneImg = document.createElement('img');
    doneImg.id = 'deleteFeat_' + myFeatureLayerName;
    doneImg.src = imgURL + 'icons/DELETE_off.png';
    doneImg.style.margin = '3px';
    doneImg.title = 'Delete feature';
    doneImg.onclick = this.deleteFeature;
    newEl.appendChild(doneImg);


    //Create the dojo panel to be loaded into the accordion
    //can use a normal dom element for the content
    new dijit.layout.ContentPane({
        id: myFeatureLayerName +'_input',
        title: panelTitle,
        onShow: function(){app.layers[this.id.split('_')[0]].activateControls();},
        onHide: function(){app.layers[this.id.split('_')[0]].deactivateControls();}
    }).placeAt('inputsTab');

    //Add the toolbar to the content pane
    new dijit.layout.ContentPane({
      content:newEl,
      style:"height:33px"
    }).placeAt(myFeatureLayerName +'_input');

    this.dataColumns = dataColumns;
    this.inputData = {
      "label": myFeatureLayerName + '_input_JSON',
      "identifier": 'fid',
      "items": []
    };

    //    set the layout structure:
    var gridLayout = [];
    for (var i=0;i<dataColumns.length;i++){
        gridLayout.push({'field':dataColumns[i].dataField,
                         'name' :dataColumns[i].displayField,
                         'width':dataColumns[i].width});
    }

    // create a new grid:
    this.attributeGrid = new dojox.grid.DataGrid({
        query: { Title: '*' },
        clientSort: true,
        rowSelector: '15px',
        structure: gridLayout,
        selectionMode: 'single'
    }, document.createElement('div'));

    this.attributeGrid.startup();
    this.attributeGrid.domNode.style.height = '100%';

    new dijit.layout.ContentPane({
      content:this.attributeGrid.domNode,
      style:"overflow: auto; height:85%"
    }).placeAt(myFeatureLayerName +'_input');

    //Create data store and bind to grid.
    this.featureStore = new dojo.data.ItemFileWriteStore({ data: this.inputData });
    this.attributeGrid.setStore(this.featureStore);

    var thisAttributeGrid = this.attributeGrid;
    var thisAttributeGridRowClick = this.attributeGridRowClick
    dojo.connect(thisAttributeGrid, "onRowClick", thisAttributeGridRowClick);
    var thisAttributeGridRowDoubleClick = this.attributeGridRowDoubleClick;
    dojo.connect(thisAttributeGrid, "onRowDblClick", thisAttributeGridRowDoubleClick);

    this.deleteButton = document.getElementById('deleteFeat_' + myFeatureLayerName);
}

//load a feature parsed from geojson, add to vector layer and dojo grid
MyFeatureLayer.prototype.loadFeature = function(feature, geoJsonParser) {
    this.geojson.features.push(feature);
    var newFeat = geoJsonParser.parseFeature(feature);
    newFeat.fid = feature.properties.fid.toString();
    this.vectorLayer.addFeatures([newFeat]);
    var newDataItem = {};
    for (var i=0;i<this.dataColumns.length;i++){
        newDataItem[this.dataColumns[i].dataField] = feature.properties[this.dataColumns[i].dataField];
    }
    this.featureStore.newItem(newDataItem);
    this.featureStore.save();
    //render attribute grid called after all loading is complete
};

//Remove event listeners when the panel is closed
MyFeatureLayer.prototype.deactivateControls = function(){
    //Update the radio button selection and tool image indicators
    var thisMyFeatureLayerName = this.myFeatureLayerName;
    document.getElementById(thisMyFeatureLayerName + '_DONE').checked = true;
    var layerRadioButtons = document.getElementsByName(thisMyFeatureLayerName + '_inputRadio');
    for (var i=0;i<layerRadioButtons.length;i++){
        var toolId = layerRadioButtons[i].id;
        var toolType = toolId.split('_')[1];
        var toolLabelImg = document.getElementById(toolId + '_imgLabel');
        var toolLabelImgSrc = toolLabelImg.src;
        if (toolType == 'DONE')
            toolLabelImg.src = toolLabelImgSrc.replace('_off','_on');
        else
            toolLabelImg.src = toolLabelImgSrc.replace('_on','_off');
    }
    //Manually deactivate the controls
    this.selectControl.unselectAll();
    this.selectControl.deactivate();
    for (var key in this.drawControls)
        this.drawControls[key].deactivate();

    //Clear grid selection
    this.attributeGrid.selection.clear();

    var delSrc = app.layers[app.currentLayer].deleteButton.src;
    app.layers[app.currentLayer].deleteButton.src = delSrc.replace('_on','_off');
};

//Activate the event listeners when the layer panel is opened
MyFeatureLayer.prototype.activateControls = function(){
    app.currentLayer = this.myFeatureLayerName;
    this.selectControl.activate();
};

//On add feature, send to server, add to grid row, populate with default properties
MyFeatureLayer.prototype.addFeature = function(feat) {
    var theFeat = feat.feature;
    var wkt = app.wktParser.write(feat.feature);
    var geoJSONObj = JSON.parse(app.geoJsonParser.write(feat.feature));
    var geomType = geoJSONObj.geometry.type;
    var srid = geoJSONObj.crs.properties.name;

    var newFeatureData = {"srid": srid,
                        "geomType": geomType,
                        "geomWKT": wkt,
                        "currentLayer": app.currentLayer};

    $.ajax({
        url: $SCRIPT_ROOT + '/map/addfeature',
        type: 'POST',
        data: newFeatureData,
        success: function (response) {
            var responseFID = response.fid;
            if (responseFID > 0) {
                theFeat.fid = responseFID.toString();
                theFeat.attributes['fid'] = responseFID
                theFeat.state = null;


                var featProps = response.featureProperties;
                var newDataItem = {};
                var dataColumns = app.layers[app.currentLayer].dataColumns;
                for (var i=0;i<dataColumns.length;i++){

                    newDataItem[dataColumns[i].dataField] = featProps[dataColumns[i].dataField];
                }
                app.layers[app.currentLayer].featureStore.newItem(newDataItem);
                app.layers[app.currentLayer].featureStore.save();
                app.layers[app.currentLayer].attributeGrid.render();
            }
            else {
                theFeat.destroy();
                switch (responseFID) {
                    case -1:
                        alert("Feature must not have self intersections");
                        break;
                    case -2:
                        alert("Feature type not recognized");
                        break;
                }
            }
        },
        error: function (xhr, ajaxOptions, thrownError) {
            alert(xhr.status);
            alert(thrownError);
        }
    });
}

//Modify feature geometry
MyFeatureLayer.prototype.modifyFeature = function(feat) {
    var theFeat = feat.feature;
    var featureBackup = new OpenLayers.Feature.Vector(theFeat.modified.geometry, theFeat.attributes);
    var wkt = app.wktParser.write(feat.feature);
    var geoJSONObj = JSON.parse(app.geoJsonParser.write(feat.feature));
    var srid = geoJSONObj.crs.properties.name;

    var modifyFeatureData = {"srid": srid,
                        "fid": theFeat.fid,
                        "geomWKT": wkt};

    $.ajax({
        url: $SCRIPT_ROOT + '/map/editfeaturegeom',
        type: 'POST',
        data: modifyFeatureData,
        success: function (response) {
            console.log(response);
            var responseFID = response.fid;
            if (responseFID > 0) {
                theFeat.state = theFeat.modified = null;
            }
            else {
                theFeat.destroy();
                app.layers[app.currentLayer].vectorLayer.events.unregister(
                    "featureadded", null, app.layers[app.currentLayer].addFeature);
                featureBackup.fid = modifyFeatureData.fid.toString();
                console.log(modifyFeatureData);
                app.layers[app.currentLayer].vectorLayer.addFeatures([featureBackup]);
                console.log(featureBackup.fid);
                app.layers[app.currentLayer].vectorLayer.events.register(
                    "featureadded", null, app.layers[app.currentLayer].addFeature);

                switch (responseFID) {
                    case -1:
                        alert("Feature must not have self intersections");
                        break;
                    case -2:
                        alert('Other Error');
                        break;
                }
            }
        },
        error: function (xhr, ajaxOptions, thrownError) {
            alert(xhr.status);
            alert(thrownError);
        }
    });
};

//On map select, select the corresponding grid row, an additional comment, another comment
MyFeatureLayer.prototype.selectFeature = function(feat) {
    var theFeat = feat.feature;
    var clickedFeatureFid = parseInt(theFeat.fid);
    var gridItems = app.layers[app.currentLayer].attributeGrid.store._arrayOfAllItems;
    var dataItemToSelect = null;
    for (var i= 0;i<gridItems.length;i++){
        //weird case that the length doesn't update
        //skip the null values
        if (!gridItems[i])
            continue;
        //if this is the right value, assign to variable and break
        if (clickedFeatureFid == gridItems[i].fid[0]){
            dataItemToSelect = gridItems[i];
            break;
        }
    }
//    select takes either an object or an index
    app.layers[app.currentLayer].attributeGrid.selection.select(dataItemToSelect);
    var delSrc = app.layers[app.currentLayer].deleteButton.src;
    app.layers[app.currentLayer].deleteButton.src = delSrc.replace('_off','_on');
};

//On map unselect, unselect the grid row
MyFeatureLayer.prototype.unselectFeature = function(feat){
    //Clear grid selection
    app.layers[app.currentLayer].attributeGrid.selection.clear();
    var delSrc = app.layers[app.currentLayer].deleteButton.src;
    app.layers[app.currentLayer].deleteButton.src = delSrc.replace('_on','_off');
};

//Select vector feature on row click
MyFeatureLayer.prototype.attributeGridRowClick = function(evt){
    //Temporarily disable the select and unselect feature listeners
    app.layers[app.currentLayer].vectorLayer.events.unregister(
            "featureselected", null,
            app.layers[app.currentLayer].selectFeature);
    app.layers[app.currentLayer].vectorLayer.events.unregister(
            "featureunselected", null,
            app.layers[app.currentLayer].unselectFeature);

    app.layers[app.currentLayer].selectControl.unselectAll();
    var clickedFID = app.layers[app.currentLayer].attributeGrid.getItem(evt.rowIndex).fid[0].toString();
    var clickedFeature = app.layers[app.currentLayer].vectorLayer.getFeatureByFid(clickedFID);
    app.layers[app.currentLayer].selectControl.select(clickedFeature);
    //set delete to on
    var delSrc = app.layers[app.currentLayer].deleteButton.src;
    app.layers[app.currentLayer].deleteButton.src = delSrc.replace('_off','_on');
    //Reregister the featureselected listener
    app.layers[app.currentLayer].vectorLayer.events.register(
            "featureselected", null,
            app.layers[app.currentLayer].selectFeature);
    app.layers[app.currentLayer].vectorLayer.events.register(
            "featureunselected", null,
            app.layers[app.currentLayer].unselectFeature);

};

//zoom to feature on grid double click
MyFeatureLayer.prototype.attributeGridRowDoubleClick = function(evt){
    var clickedFID = app.layers[app.currentLayer].attributeGrid.getItem(evt.rowIndex).fid[0].toString();
    var clickedFeature = app.layers[app.currentLayer].vectorLayer.getFeatureByFid(clickedFID);
    var bounds = clickedFeature.geometry.getBounds();
    map.zoomToExtent(bounds, false);
};

//Delete Feature on server, map, and grid
MyFeatureLayer.prototype.deleteFeature = function(){
    var selectedFeatures = app.layers[app.currentLayer].vectorLayer.selectedFeatures;
    if (selectedFeatures.length == 0)
        return;
    var selectedFeature = selectedFeatures[0];
    var deleteFID = parseInt(selectedFeature.fid);
    $.ajax({
        url: $SCRIPT_ROOT + '/map/deletefeature',
        type: 'POST',
        data: {"deleteFID":deleteFID},
        success: function (response) {
            if (response.success == 0){
                app.layers[app.currentLayer].attributeGrid.removeSelectedRows();
                app.layers[app.currentLayer].selectControl.unselectAll();
                selectedFeature.destroy();
            }
            else
                console.log('Something wrong');
        },
        error: function (xhr, ajaxOptions, thrownError) {
            alert(xhr.status);
            alert(thrownError);
        }
    });
};