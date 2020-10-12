"use strict"

var curr_visualization = {
    dataset: "vega-lite-example-gallery",
    name: "bar_grouped",
    filename: "bar_grouped.json"
};

const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

window.onload = init;

async function init() {
    initSpecHandler();
    extractDataTable(buildSpecFileDir(curr_visualization));
}

function buildSpecFileDir(visualization) {
    return "./data/" + visualization.dataset + "/specs/" + visualization.filename;
}

function extractDataTable(specFileDir) {
    var jsQuery = "#vis-container";

    vegaEmbed(jsQuery, specFileDir)
    .then(function(vegaData) {
        let vis2dataMapping = specHandler.extractMapping(vegaData.spec);
        let temporals = vis2dataMapping["temporals"];
        (function() {
            function waitUntilValueFilled() {
                setTimeout(function() {
                    if (vegaData.view._runtime.data["source_0"].values.value) {
                        let filteredVisualizationData = JSON.parse(JSON.stringify(vegaData.view._runtime.data["source_0"].values.value));

                        let headers = Object.keys(filteredVisualizationData[0]);
                        let headersToDelete = [];
                        let headersToAlterMap = {};
                        headers.forEach(function(header) {
                            if (header.replace("\\n", "").split(/[^a-zA-Z0-9\"]/).join("").length === 0 || header.substring(header.length - 6) === "_start" || header.substring(header.length - 4) === "_end") {
                                headersToDelete.push(header);
                                return;
                            }
                            if (header.substring(header.length - 2) === "_*") {
                                headersToAlterMap[header] = header.substring(0, header.length - 2);
                                return;
                            }
                            if (header.substring(0, 4) === "sum_") {
                                headersToAlterMap[header] = header.substring(4);
                                return;
                            }

                            if (header.substring(0, 7) === "median_") {
                                headersToAlterMap[header] = header.substring(7);
                                return;
                            }

                            if (header.substring(0, 6) === "month_") {
                                headersToAlterMap[header] = "month";
                                return;
                            }

                            if ((JSON.stringify(vegaData.spec.encoding)).replace("\\n", "").split(/[^a-zA-Z0-9\"]/).join("").indexOf(('"' + header + '"').split(/[^a-zA-Z0-9\"]/).join("")) < 0) {
                                headersToDelete.push(header);
                                return;
                            }

                            var valuesSet = new Set();
                            filteredVisualizationData.forEach(function(filteredVisualizationDatum) {
                                valuesSet.add(filteredVisualizationDatum[header]);
                                if (String(filteredVisualizationDatum[header]).match(/^-?\d{1,3}(?:,\d{3})+(?:\.\d*)?$/)) {
                                    headersToDelete.push(header);
                                    return;
                                }
                            });
                            if (valuesSet.size === 1 && valuesSet.has(null)) {
                                headersToDelete.push(header);
                                return;
                            }
                        });
                        let headersToAlter = Object.keys(headersToAlterMap);
                        filteredVisualizationData.forEach(function(filteredVisualizationDatum) {
                            headersToDelete.forEach(function(headerToDelete) {
                                delete filteredVisualizationDatum[headerToDelete];
                            });
                            headersToAlter.forEach(function(headerToAlter) {
                                filteredVisualizationDatum[headersToAlterMap[headerToAlter]] = filteredVisualizationDatum[headerToAlter];
                                delete filteredVisualizationDatum[headerToAlter];
                            })
                        });
                        console.log(filteredVisualizationData);

                        temporals.forEach(function(temporal) {
                            if (temporal.unit !== null) {
                                if (temporal.unit === "month") {
                                    filteredVisualizationData.forEach(function(filteredVisualizationDatum) {
                                        var parsedDate = new Date(filteredVisualizationDatum["month"]);
                                        var month = parsedDate.getMonth();
                                        filteredVisualizationDatum["month"] = monthNames[month];
                                    });
                                }
                            } else {
                                let minUnit = "days";
                                let years = new Set();
                                let months = new Set();
                                let days = new Set();

                                filteredVisualizationData.forEach(function(filteredVisualizationDatum) {
                                    var parsedDate = new Date(filteredVisualizationDatum[temporal.field]);
                                    var year = parsedDate.getFullYear();
                                    var month = parsedDate.getMonth();
                                    var day = parsedDate.getDate();
                                    years.add(year);
                                    months.add(month);
                                    days.add(day);
                                });

                                if (days.size === 1) {
                                    minUnit = "months";
                                    if (months.size === 1) {
                                        minUnit = "years";
                                    }
                                }
                                

                                filteredVisualizationData.forEach(function(filteredVisualizationDatum) {
                                    var parsedDate = new Date(filteredVisualizationDatum[temporal.field]);
                                    var year = parsedDate.getFullYear();
                                    var month = parsedDate.getMonth();
                                    var day = parsedDate.getDate();
                                    var dateString = "";
                                    if (minUnit === "years") {
                                        if (month === 11 && day === 31) {
                                            year += 1;
                                        }
                                        dateString = String(year);
                                    } else if (minUnit === "months") {
                                        dateString = monthNames[month] + ", " + String(year)
                                    } else if (minUnit === "days") {
                                        dateStrng = monthNames[month] + " " + String(day) + ", " + String(year)
                                    }
                                    filteredVisualizationDatum[temporal.field] = dateString;
                                });
                            }
                        });


                        let foldedVisualizationData = foldData(filteredVisualizationData, vis2dataMapping);


                        let foldedTable = foldIntoTable(foldedVisualizationData);
                        document.getElementById("table-container").appendChild(generateHTMLTable(foldedTable));
                        
                        console.log(tableToCSV(foldedTable));
                    }
                    else {
                        waitUntilValueFilled();
                    }
                }, 300);
            }
            waitUntilValueFilled();
        })();
    })
    .catch(console.error);
}

function foldData(tableEntries, vis2dataMapping) {
    var foldResult = [];
    var originalHeaders = Object.keys(tableEntries[0]);

    if (originalHeaders.length !== 3) {
        return tableEntries;
    }
    var markType = vis2dataMapping.mark;
    vis2dataMapping = vis2dataMapping.mappings;

    var majorAxis;
    if (markType === "bar") {
        if ("columnX" in vis2dataMapping.forwardMap) {
            majorAxis = vis2dataMapping.forwardMap.columnX;
        } else if ("rowY" in vis2dataMapping.forwardMap) {
            majorAxis = vis2dataMapping.forwardMap.rowY;
        } else if ("positionX" in vis2dataMapping.forwardMap) {
            majorAxis = vis2dataMapping.forwardMap.positionX;
        } else if ("positionY" in vis2dataMapping.forwardMap) {
            majorAxis = vis2dataMapping.forwardMap.positionY;
        } else {
            return tableEntries;
        }
    } else if (markType === "line") {
        if ("color" in vis2dataMapping.forwardMap) {
            majorAxis = vis2dataMapping.forwardMap.color;
        } else {
            return tableEntries;
        }
    }

    if (!majorAxis) {
        return tableEntries;
    }

    // Preliminary pass
    var majorAxisValueCounts = {};
    var fieldValuesByMajorAxisValue = {};
    var fieldValues = {};

    tableEntries.forEach(function(tableEntry) {
        var majorAxisValue = tableEntry[majorAxis];
        if (!(majorAxisValue in majorAxisValueCounts)) {
            majorAxisValueCounts[majorAxisValue] = 1;
        } else {
            majorAxisValueCounts[majorAxisValue] += 1;
        }

        originalHeaders.forEach(function(originalHeader) {
            if (originalHeader === majorAxis) {
                return;
            }
            if (!(originalHeader in fieldValues)) {
                fieldValues[originalHeader] = new Set();
            }
            if (!(originalHeader in fieldValuesByMajorAxisValue)) {
                fieldValuesByMajorAxisValue[originalHeader] = {};
            }
            if (!(majorAxisValue in fieldValuesByMajorAxisValue[originalHeader])) {
                fieldValuesByMajorAxisValue[originalHeader][majorAxisValue] = new Set();
            }
            fieldValues[originalHeader].add(tableEntry[originalHeader]);
            fieldValuesByMajorAxisValue[originalHeader][majorAxisValue].add(tableEntry[originalHeader]);
        });
    });

    // Figure out the minor axis
    var minorAxis;
    var dataField;
    var majorMaxRepeat = Math.max.apply(null, Object.values(majorAxisValueCounts));
    var candidateFields = Object.keys(fieldValues);
    candidateFields.forEach(function(candidateField) {
        if (fieldValues[candidateField].size <= majorMaxRepeat) {
            minorAxis = candidateField;
        } else {
            dataField = candidateField;
        }
    });

    if (!minorAxis) {
        return tableEntries;
    }

    if (!(majorAxis in tableEntries[0] && minorAxis in tableEntries[0] && dataField in tableEntries[0])) {
        return tableEntries;
    }

    // Now the actual folding
    var foldedData = [];
    var majorAxisValues = Object.keys(majorAxisValueCounts);
    majorAxisValues.forEach(function(majorAxisValue) {
        var foldedDatum = {};
        foldedDatum[majorAxis] = majorAxisValue;
        tableEntries.forEach(function(tableEntry) {
            if (String(tableEntry[majorAxis]) !== String(majorAxisValue)) {
                return;
            }
            foldedDatum[tableEntry[minorAxis]] = tableEntry[dataField];
        });
        foldedData.push(foldedDatum);
    });

    return foldedData;
}

function foldIntoTable(tableEntries) {
    var rawHeader = Object.keys(tableEntries[0]);
    var numberHeaders = [];
    var yearHeaders = [];
    var nonNumberHeaders = [];
    rawHeader.forEach(function(headerElem) {
        var isNumberHeader = true;
        tableEntries.forEach(function(tableEntry) {
            if (tableEntry[headerElem] === null || tableEntry[headerElem] === undefined || String(tableEntry[headerElem]).match(/^\d+(?:.\d*)?$/) !== null) {
                return;
            } else {
                isNumberHeader = false;
            }
        });
        if (isNumberHeader) {
            if (headerElem === "year" || headerElem === "Year") {
                yearHeaders.push(headerElem);
            } else {
                numberHeaders.push(headerElem);
            }
        } else {
            nonNumberHeaders.push(headerElem);
        }
    });

    var foldedTable = [];
    foldedTable.push(nonNumberHeaders.concat(yearHeaders.concat(numberHeaders)));

    tableEntries.forEach(function(tableEntry) {
        var newRow = [];
        foldedTable[0].forEach(function(header) {
            newRow.push(tableEntry[header]);
        });
        foldedTable.push(newRow);
    });
    return foldedTable;
}

function generateHTMLTable(foldedTable) {
    var htmlTable = document.createElement("table");
    foldedTable.forEach(function(tableRow) {
        var htmlRow = document.createElement("tr");
        tableRow.forEach(function(tableElem) {
            var htmlElem = document.createElement("td");
            htmlElem.textContent = tableElem;
            htmlRow.appendChild(htmlElem);
        });
        htmlTable.appendChild(htmlRow);
    });
    console.log(htmlTable)
    return htmlTable;
}

function tableToCSV(table) {
    var csvText = "\"";
    table.forEach(function(row) {
        csvText += row.join("\",\"") + "\"\n\"";
    });
    csvText = csvText.slice(0, -1);

    return csvText;
}