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


// MOBILE NAV
menuButton.addEventListener("click", function () {
    sidebar.classList.toggle("open");
});


// SAMPLE DASHBOARD DATA
const defaultDashboardData = {
    totalTrips: "120,000",
    averageDistance: "4.6mi",
    averageFare: "$24.60",
    averageDuration: "18.4 min"

};

const filteredDashboardData = {
    totalTrips: "68,420",
    averageDistance: "5.3 mi",
    averageFare: "$27.10",
    averageDuration: "20.2 min"
};


// UPDATE DASHBOARD
function updateDashboard(data) {

    totalTrips.textContent = data.totalTrips;
    averageDistance.textContent = data.averageDistance;
    averageFare.textContent = data.averageFare;
    averageDuration.textContent = data.averageDuration;
}


// APPLY FILTERS
applyFiltersButton.addEventListener("click", function () {
    console.log("Selected Filters:");

    console.log({
        date: dateFilter.value,

        pickupLocation:
            pickupFilter.value,
        distance:
            distanceFilter.value,
        fare:
            fareFilter.value
    });

    //To be Replaced with fetch() request
    updateDashboard(
        filteredDashboardData
    );

    applyFiltersButton.textContent = "Filters applied";

    setTimeout(function () {
        applyFiltersButton.textContent = "Apply filters";
    }, 1200);

});


// RESET FILTERS
resetFiltersButton.addEventListener(
    "click",
    function() {
        dateFilter.value = "";
        pickupFilter.value = "";
        distanceFilter.value = "";
        fareFilter.value = "";

        updateDashboard(
            defaultDashboardData
        );
    
    }

);

//DETAIL DRAWER
const detailDrawer = document.getElementById("detailDrawer");
const drawerBackdrop = document.getElementById("drawerBackdrop");
const drawerClose = document.getElementById("drawerClose");

document.addEventListener(
    "keydown",
    function (event) {

        if (
            event.key === "Escape"
        ) {

            closeDrawer();
            closeMobileSidebar();
        }
    }
);

const sidebarBackdrop = document.getElementById("sidebarBackdrop");
function openMobileSidebar() {

    sidebar.classList.add (
        "open"
    );

    sidebarBackdrop.classList.add(
        "open"
    );
}

function closeMobileSidebar (){
    sidebar.classList.remove(
        "open"
    );

    sidebarBackdrop.classList.remove("open");
}

menuButton.addEventListener(
    "click",
    function () {

        const isOpen = sidebar.classList.contains(
            "open"
        );

        if (isOpen) {
            closeMobileSidebar();
        }else{

            openMobileSidebar();
        }
    }
);

sidebarBackdrop.addEventListener(
    "click",
    closeMobileSidebar
);



// SIDEBAR NAVIGATION
const navigationItems = document.querySelectorAll(".nav-item");

navigationItems.forEach(function (item) {

    item.addEventListener(
        "click",
        function () {

            navigationItems.forEach(
                function(navItem) {
                    navItem.classList.remove("active");
                }
            );

            item.classList.add("active");

            //Close sidebar automatically on mobile

            if (window.innerWidth <= 768){
                sidebar.classList.remove(
                    "open"
                );
            }
        }
    );
});


// INITAL APP STATE 
updateDashboard(defaultDashboardData);

console.log("Urban Mobility Data Explorer loaded.");
