// DOM ELEMENT CONST VARS

const sidebar = document.getElementById("sidebar");
const menuButton = document.getElementById("menuButton")
const applyFiltersButton = document.getElementById("applyFilters");
const resetFiltersButton = document.getElementById("resetFilters");
const dateFilter = document.getElementById("dateFilter");
const pickupFilter = document.getElementById("pickupFilter");
const distanceFilter = document.getElementById("distanceFilter");
const fareFilter = document.getElementById("fareFilter");
const totalTrips = document.getElementById("totalTrips");
const averageDistance = document.getElementById("averageDistance");
const averageFare = document.getElementById("averageFare");
const averageDuration = document.getElementById("averageDuration");

menuButton.addEventListener("click", function () {
    sidebar.classList.toggle("open");
})