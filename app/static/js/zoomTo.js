var getSelectedRadioButton = function (groupName) {
    var buttons = document.getElementsByName(groupName);
    if (buttons.length == 0){
        alert("Check group name: " + groupName);
    }
    else{
        for (var i = 0; i <= buttons.length; i++) {
            if (buttons[i].checked) {
                return buttons[i];
            }
        }
    }

}

function isNumber(n) {
    return !isNaN(parseFloat(n)) && isFinite(n);
}

function isInt(n) {
    return parseFloat(n) == parseInt(n, 10) && !isNaN(n) && n%1 == 0;
} // 6 characters











//Zoom Area of Interest
//Radio Button Switcher for Search Method
var DDDegMinOnChange = function () {
    switch (getSelectedRadioButton("LatLongEntryMethod").value) {
        case "DD":
            document.getElementById('DDFieldset').style.display='';
            document.getElementById('DegMinFieldSet').style.display = 'none'; 
            document.getElementById('GoogLocSearch').style.display = 'none';
            break;
        case "DegMin":
            document.getElementById('DDFieldset').style.display = 'none';
            document.getElementById('DegMinFieldSet').style.display = '';
            document.getElementById('GoogLocSearch').style.display = 'none';
            break;
        case "googleSearch":
            document.getElementById('DDFieldset').style.display = 'none';
            document.getElementById('DegMinFieldSet').style.display = 'none';
            document.getElementById('GoogLocSearch').style.display = '';
            break;
        default:
            alert("check error");
            break;
    }
}


var zoomToLocation = function () {
    document.getElementById("zoomToError").innerHTML = "";
    var errorString;
    var lat, lng;
    var zoomToLatLon = function (lat, lon) {
        map.setCenter(new OpenLayers.LonLat(lon, lat).transform(
        new OpenLayers.Projection("EPSG:4326"),
        map.getProjectionObject()
    ), 14);
    }

    switch (getSelectedRadioButton("LatLongEntryMethod").value) {
        case "DD":
            //validate inputs
            var LatDDVal = document.getElementById("inputLatDD").value;
            var LngDDVal = document.getElementById("inputLonDD").value;

            //Check Latitude Input
            if (isNumber(LatDDVal) && LatDDVal >= 0 && LatDDVal <= 90) {
                lat = LatDDVal * parseInt(document.getElementById('DDLatSelect').value);
                document.getElementById("inputLatDD").className = "";
            }
            else {
                document.getElementById("inputLatDD").className = "coordinateInvalid";
                document.getElementById("zoomToError").innerHTML = "Lat field must be positive number between 0 and 90";
                return;
            }
            //Check Longitude Input
            if (isNumber(LngDDVal) && LngDDVal >= 0 && LngDDVal <= 180) {
                lng = LngDDVal * parseInt(document.getElementById('DDLonSelect').value);
                document.getElementById("inputLonDD").className = "";
            }
            else {
                document.getElementById("inputLonDD").className = "coordinateInvalid";
                document.getElementById("zoomToError").innerHTML = "Long field must be positive number between 0 and 180";
                return;
            }
            zoomToLatLon(lat, lng);
            break;
        case "DegMin":
            var LatDegVal = document.getElementById("inputLatDeg").value;
            var LatMinVal = document.getElementById("inputLatMin").value;
            var LngDegVal = document.getElementById("inputLonDeg").value;
            var LngMinVal = document.getElementById("inputLonMin").value;
            //Check Latitude Deg Input
            if (isInt(LatDegVal) && LatDegVal >= 0 && LatDegVal <= 90) {
                 document.getElementById("inputLatDeg").className = "";
            }
            else {
                document.getElementById("inputLatDeg").className = "coordinateInvalid";
                document.getElementById("zoomToError").innerHTML = "Lat Deg field must be positive integer between 0 and 90";
                return;
            }
            //Check Latitude Min Input
            if (isNumber(LatMinVal) && LatMinVal >= 0 && LatMinVal <= 60) {
                document.getElementById("inputLatMin").className = "";
                lat = (parseInt(LatDegVal) + (parseFloat(LatMinVal) / 60)) * parseInt(document.getElementById('DegMinLatSelect').value);
            }
            else {
                document.getElementById("inputLatMin").className = "coordinateInvalid";
                document.getElementById("zoomToError").innerHTML = "Lat Min must be positive number between 0 and 60";
                return;
            }
            //Check Longitude Deg Input
            if (isInt(LngDegVal) && LngDegVal >= 0 && LngDegVal <= 180) {
                document.getElementById("inputLonDeg").className = "";
            }
            else {
                document.getElementById("inputLonDeg").className = "coordinateInvalid";
                document.getElementById("zoomToError").innerHTML = "Long Deg field must be positive integer between 0 and 180";
                return;
            }
            //Check Longitude Min Input
            if (isNumber(LngMinVal) && LngMinVal >= 0 && LngMinVal <= 60) {
                document.getElementById("inputLonMin").className = "";
                lng = (parseInt(LngDegVal) + (parseFloat(LatMinVal) / 60)) * parseInt(document.getElementById('DegMinLonSelect').value);
            }
            else {
                document.getElementById("inputLonMin").className = "coordinateInvalid";
                document.getElementById("zoomToError").innerHTML = "Long Min must be positive number between 0 and 60";
                return;
            }
            zoomToLatLon(lat, lng);
            break;
        case "googleSearch":
            var address = document.getElementById("textSearch").value;

            var geocoder = new google.maps.Geocoder();
            geocoder.geocode({ 'address': address },
                function (results, status) {
                    if (status == google.maps.GeocoderStatus.OK) {
                        if (results.length > 1) {
                            document.getElementById("zoomToError").innerHTML = "Multiple Results. Please Refine your search";
                        }
                        else {
                            lat = results[0].geometry.location.lat();
                            lng = results[0].geometry.location.lng();
                            zoomToLatLon(lat, lng);

                        }
                    }
                    else {
                        document.getElementById("zoomToError").innerHTML = "No Results Found";
                    }

                });
            break;
        default:
            alert("check error");
            break;
    }

}


function SetProjExtent() {
    //left_ext, bottom_ext, right_ext,  top_ext
    //Get the controls
    //var txtresult = $get("txtSum");
    var mapextent = map.getExtent();
    var param = {
        "left_ext": mapextent.left,
        "bottom_ext":  mapextent.bottom,
        "right_ext": mapextent.right,
        "top_ext": mapextent.top
    };
    $.ajax({
        url: 'Default.aspx/SetExtent',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(param),  //"Parameters":"Must be JSON strings!"
        success: function (response) {
            // Don't forget that the response is wrapped in a
            //  ".d" object in ASP.NET 3.5 and later.
            document.getElementById("StatusLabel").innerHTML = response.d;
            console.log(response.d);
        },
        error: function (xhr, ajaxOptions, thrownError) {
            alert(xhr.status);
            alert(thrownError);
        }
    });
}




