function ExtentLayer(olMap, projectConfig, radioButtonTagName) {
    //Define the layer style and layer
    var vector_style = new OpenLayers.Style({
        'fillColor': '#FF00BF',
        'fillOpacity': 0,
        'strokeColor': '#FF00BF',
        'strokeOpacity': .8,
        'strokeWidth': 1,
        'pointRadius': 5
    });

    var vector_style_select = new OpenLayers.Style({
        'fillColor': '#FF00BF',
        'fillOpacity': .25,
        'strokeColor': '#FF00BF',
        'strokeOpacity': 1,
        'strokeWidth': 2,
        'pointRadius': 5
    });

    var vector_style_map = new OpenLayers.StyleMap({
        'default': vector_style,
        'select': vector_style_select
    });

    this.extentLayer = new OpenLayers.Layer.Vector('extentLayer', {
        'styleMap': vector_style_map,
        'renderers': app.renderer
    });

    var thisExtentLayer = this.extentLayer;

    olMap.addLayer(thisExtentLayer);

    //All Draw controls are initialized, only those relevant to this layer will be loaded
    this.drawControls = {
        'DONE':{activate:function(){},deactivate:function(){}},
        'POLYGON': new OpenLayers.Control.DrawFeature(this.extentLayer, OpenLayers.Handler.Polygon),
        'MODIFY': new OpenLayers.Control.ModifyFeature(this.extentLayer)
    };

    olMap.addControls([this.drawControls.POLYGON,this.drawControls.MODIFY]);

    this.extentRadioButtons = document.getElementsByName(radioButtonTagName);

    this.deactivateAll();

    if (projectConfig.geom){
        var newFeat = new OpenLayers.Feature.Vector();
        newFeat.fid = '1000000';
        var newGeom = app.geoJsonParser.parseGeometry(projectConfig.geom);
        newFeat.geometry = newGeom;
        var bounds = newGeom.getBounds();
        map.zoomToExtent(bounds, false);
        this.extentLayer.addFeatures([newFeat]);
    }

    //Add the event listeners after loading
    this.extentLayer.events.on({
        "featureadded": this.addFeature,
        "afterfeaturemodified": this.modifyFeature
        });
}

//Activate the selected extent layer drawing tool
ExtentLayer.prototype.radioChanged = function(){
    for (var i= 0;i<this.extentRadioButtons.length;i++){
        var elId = this.extentRadioButtons[i].id;
        var toolName = elId.split('_')[0];
        var imgLabel = document.getElementById(elId + '_imgLabel');
        var imgLabelSrc = imgLabel.src;
        if (this.extentRadioButtons[i].checked){
            //activate the control and the 'active' button
            imgLabel.src = imgLabelSrc.replace('_off','_on');
            this.drawControls[toolName].activate();
        }
        else{
            imgLabel.src = imgLabelSrc.replace('_on','_off');
            this.drawControls[toolName].deactivate();
        }
    }
};

//Deactivate the controls when the panel is closed
ExtentLayer.prototype.deactivateAll = function(){
    for (var i = 0; i< this.extentRadioButtons.length; i++){
        var theId = this.extentRadioButtons[i].id;
        var toolType = theId.split('_')[0];
        var theLabelImg = document.getElementById(theId + '_imgLabel');
        var theLabelImgSrc = theLabelImg.src;
        if (toolType == 'DONE'){
            this.drawControls[toolType].activate();
            this.extentRadioButtons[i].checked = true;
            theLabelImg.src = theLabelImgSrc.replace('_off','_on');
        }
        else{
            this.drawControls[toolType].deactivate();
            theLabelImg.src = theLabelImgSrc.replace('_on','_off');
        }
    }
};

//Add the extent feature, check if there is only one, update on server
ExtentLayer.prototype.addFeature = function(feat){
    var theFeat = feat.feature;

    if (app.extentLayer.extentLayer.features.length > 1) {
        alert('A project can have only one extent. \nPlease clear the extent or modify the existing.');
        theFeat.destroy();
        return;
    }
    if (theFeat.geometry.getArea() > 2 * 32534032){
        alert('The selected extent is too large.  Please select a smaller area');
        theFeat.destroy();
        return;
    }
//    theFeat.destroy();
    var wkt = app.wktParser.write(theFeat);
    var geoJSONObj = JSON.parse(app.geoJsonParser.write(theFeat));
    var srid = geoJSONObj.crs.properties.name;

    var updateExtObj = {"updatetask": 1,
                    "srid": srid,
                    "geomWKT": wkt};

    $.ajax({
        url: $SCRIPT_ROOT + '/map/updateextent',
        type: 'POST',
        data: updateExtObj,
        success: function (response) {
            if (response.code == 1) {
                projectProperties.geom = response.extGSJN;
                theFeat.fid = '1000000';
                theFeat.attributes['fid'] = '1000000';
                theFeat.state = null;
            }
            else {
                theFeat.destroy();
                switch (response.code) {
                    case -1:
                        alert("Feature must not have self intersections");
                        break;
                    case -2:
                        alert("Other Error");
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

//Modify the extent feature, update on server
ExtentLayer.prototype.modifyFeature = function(feat){
    var theFeat = feat.feature;
    if (!theFeat.modified)
        //nothing really happened
        return;
    var featureBackup = new OpenLayers.Feature.Vector(theFeat.modified.geometry, theFeat.attributes);

    if (theFeat.geometry.getArea() > 2 * 32534032){
        alert('The selected extent is too large.  Please select a smaller area');
        theFeat.destroy();
        app.extentLayer.extentLayer.events.unregister(
            "featureadded", null, app.extentLayer.addFeature);
        featureBackup.fid = '1000000';
        app.extentLayer.extentLayer.addFeatures([featureBackup]);
        console.log(featureBackup.fid);
        app.extentLayer.extentLayer.events.register(
            "featureadded", null, app.extentLayer.addFeature);
        return;
    }

    var wkt = app.wktParser.write(theFeat);
    var geoJSONObj = JSON.parse(app.geoJsonParser.write(theFeat));
    var srid = geoJSONObj.crs.properties.name;

    var updateExtObj = {"updatetask": 2,
                    "srid": srid,
                    "geomWKT": wkt};

    $.ajax({
        url: $SCRIPT_ROOT + '/map/updateextent',
        type: 'POST',
        data: updateExtObj,
        success: function (response) {
            if (response.code == 1) {
                projectProperties.geom = response.extGSJN;
                theFeat.state = theFeat.modified = null;
            }
            else {
                theFeat.destroy();
                app.extentLayer.extentLayer.events.unregister(
                    "featureadded", null, app.extentLayer.addFeature);
                featureBackup.fid = '1000000';
                app.extentLayer.extentLayer.addFeatures([featureBackup]);
                console.log(featureBackup.fid);
                app.extentLayer.extentLayer.events.register(
                    "featureadded", null, app.extentLayer.addFeature);
                switch (response.code) {
                    case -1:
                        alert("Feature must not have self intersections");
                        break;
                    case -2:
                        alert("Other Error");
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

//Delete the extent feature in map and on server
ExtentLayer.prototype.clearExtent = function(){
    //If there is no extent set, bail out
    if (this.extentLayer.features.length == 0){
        console.log('No existing extent');
        return;
    }

    while (this.extentLayer.features.length > 0)
            this.extentLayer.features[0].destroy();
    //update on server
    $.ajax({
        url: $SCRIPT_ROOT + '/map/updateextent',
        type: 'POST',
        data: {"updatetask": 3},
        success: function (response) {
            if (response.code != 1) {
                console.log('someting wrong');
                switch (response.code) {
                    case -1:
                        alert("Feature must not have self intersections");
                        break;
                    case -2:
                        alert("Other Error");
                        break;
                }
            }
        },
        error: function (xhr, ajaxOptions, thrownError) {
            alert(xhr.status);
            alert(thrownError);
        }
    });

    projectProperties.geom = null;

};