"use strict"

function rand4() {
    return Math.floor((1 + Math.random()) * 0x10000).toString(16).substring(1);
}

function rand40() {
    var randStr = "";
    for (let i = 0; i < 10; i++) {
        randStr += rand4();
    }
    return randStr;
}

function waitUntilConditionMet(checkCondition, onConditionMet) {
	function waitHelper() {
		setTimeout(function() {
			if (checkCondition()) {
				onConditionMet();
			} else {
				waitHelper();
			}
		}, 300);
	}
	waitHelper();
}

// Bidirectional map. CAUTION: no safeguard is used.
function BidirectionalMap() {
	this.forwardMap = {};
	this.backwardMap = {};
}

BidirectionalMap.prototype.forwardKeys = function() {
	return Object.keys(this.forwardMap);
}

BidirectionalMap.prototype.backwardKeys = function() {
	return Object.keys(this.backwardMap);
}

BidirectionalMap.prototype.addForward = function(key, value) {
	this.forwardMap[key] = value;
	this.backwardMap[value] = key;
}

BidirectionalMap.prototype.addBackward = function(key, value) {
	this.addForward(value, key);
}

BidirectionalMap.prototype.getForward = function(key) {
	return this.forwardMap[key];
}

BidirectionalMap.prototype.getBackward = function(key) {
	return this.backwardMap[key];
}

BidirectionalMap.prototype.toString = function(compact = false) {
	var mapStr = "";
	for (let key in this.forwardMap) {
		mapStr += key + " <-> " + this.forwardMap[key];
		mapStr += compact ? ", " : "\n";
	}
	mapStr = mapStr.substring(0, mapStr.length - (compact ? 2 : 1));
	return mapStr;
}

BidirectionalMap.prototype.toHTML = function() {
	var htmlElem = document.createElement("div");
	htmlElem.textContent = this.toString();
	return htmlElem;
}
