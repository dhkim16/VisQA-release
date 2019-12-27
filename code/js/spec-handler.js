"use strict"

var specHandler;

function initSpecHandler() {
    specHandler = new SpecHandler();
}

function SpecHandler() {

}

SpecHandler.prototype.extractMapping = function(spec) {
    var visToDataMap = new BidirectionalMap();
    var temporals = [];
    switch(spec.mark) {
    case "bar":
        // TODO: Histogram needs special handling
        if ("x" in spec.encoding) {
            if (spec.encoding.x.type === "quantitative") {
                // This means that the bar chart is 'wide'
                visToDataMap.addForward("lengthX", spec.encoding.x.field);
                // TODO: HANDLE CASE WHEN THERE IS AGGREGATION
            } else {
                // This means that the bar chart is 'not wide'
                if ("column" in spec.encoding) {
                    visToDataMap.addForward("columnX", spec.encoding.column.field);
                }
                visToDataMap.addForward("positionX", spec.encoding.x.field);
                // TODO: HANDLE CASE WHEN THERE IS AGGREGATION


                if ("timeUnit" in spec.encoding.x) {
                    temporals.push({field: spec.encoding.x.field, unit: spec.encoding.x.timeUnit});
                }
            }
        }
        if ("y" in spec.encoding) {
            if (spec.encoding.y.type === "quantitative") {
                // This means that the bar chart is 'tall'
                visToDataMap.addForward("lengthY", spec.encoding.y.field);
            } else {
                // This means that the bar chart is 'not tall'
                if ("row" in spec.encoding) {
                    visToDataMap.addForward("rowY", spec.encoding.row.field);
                }
                visToDataMap.addForward("positionY", spec.encoding.y.field);


                if ("timeUnit" in spec.encoding.y) {
                    temporals.push({field: spec.encoding.y.field, unit: spec.encoding.y.timeUnit});
                }
            }
        }
        break;
    case "tick":
        break;
    case "point":
        break;
    case "circle":
        break;
    case "line":
        if ("y" in spec.encoding && spec.encoding.y.type === "quantitative") {
            visToDataMap.addForward("positionY", spec.encoding.y.field)
            visToDataMap.addForward("positionX", spec.encoding.x.field)


            if ("color" in spec.encoding) {
                let colorMapping = visToDataMap.addForward("color", spec.encoding.color.field);
            }
        }

        if ("x" in spec.encoding && spec.encoding.x.type === "temporal") {
            temporals.push({field: spec.encoding.x.field, unit: null});
        }
        break;
    case "text":
        break;

    default:
        break;
    }
    return {mark: spec.mark, mappings: visToDataMap, temporals: temporals};
}