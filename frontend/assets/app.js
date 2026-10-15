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
const tripTablebody = document.getElementById("tripTableBody");
const rankingList = document.getElementById("rankingList");
const boroughList = document.getElementById("boroughList");


async function fetchJSON(url) {

    const response = await fetch(url);

    if(!response.ok){
        let message = "Unable to load data";

        try {
            const error = await response.json();

            message = error.error || message;
        } catch (error) {
            console.error(error);
        }

        throw new Error(
            message
        );
    }

    return response.json();

}

function buildFilterParams() {

    const params = new URLSearchParams();

    if (dateFilter.value) {

        params.set(
            "start_date",
            dateFilter.value
        );

        params.set(
            "end_date",
            dateFilter.value
        );
    }

    if (pickupFilter.value) {

        params.set(
            "pickup_borough",
            pickupFilter.value
        );
    }

    if ( distanceFilter.value === "short" ){

        params.set ("max_distance", "3");

    } else if (distanceFilter.value === "medium"){

        params.set ("min_distance", "3");
        params.set ("max_distance", "10");

    } else if (distanceFilter.value === "long"){

        params.set ("min_distance", "10");

    }

    if (fareFilter.value === "low") {

        params.set("max_fare","15");

    } else if (fareFilter.value === "medium") {

        params.set("min_fare","15");
        params.set("max_fare","40");

    } else if (fareFilter.value === "high"){

        params.set("min_fare","40");

    }


    return params;
}

async function loadSummary(params){

    const query = params.toString();
    const data = await fetchJSON(
        query
            ? `/api/summary?${query}`
            : "/api/summary"
    );

    totalTrips.textContent = Number(data.total_trips || 0).toLocaleString();

    averageDistance.textContent = `${Number(data.avg_distance_miles || 0).toFixed(1)} mi`;

    averageFare.textContent = `$${Number(data.avg_fare || 0).toFixed(2)}`;

    averageDuration.textContent = `${Number(data.avg_duration_min || 0).toFixed(1)} min`;


}

async function loadTrips(params) {
    const tripParams = new URLSearchParams(params);

    tripParams.set("per_page","15");

    const data = await fetchJSON(`/api/trips?${tripParams}`);

    tripTablebody.innerHTML = "";

    if (data.trips.length === 0){

        tripTablebody.innerHTML =
        `<tr>
            <td colspan="6">No trips match these filters.</td>
        </tr>`;

        return;
    }

    data.trips.forEach(function (trip) {
        const row = document.createElement("tr");
        row.className = "trip-row";
        row.dataset.tripId = trip.trip_id;
        row.tabIndex = 0;
        row.innerHTML = `
            <td>${escapeHTML(trip.pickup_zone)}</td>
            <td>${escapeHTML(trip.dropoff_zone)}</td>
            <td>${Number(trip.trip_distance).toFixed(1)} mi</td>
            <td>${Number(trip.duration_min).toFixed(1)} min</td>
            <td>$${Number(trip.total_amount).toFixed(2)}</td>
            <td><span class="status-pill">Valid</span></td>`;
        row.addEventListener("click", () => loadTripDetail(row.dataset.tripId));
        row.addEventListener("keydown", event => {
            if (event.key === "Enter") loadTripDetail(row.dataset.tripId);
        });
        tripTablebody.appendChild(row);
    });
}

function escapeHTML(value) {
    return String(value ?? "—").replace(/[&<>"']/g, character => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[character]));
}

async function loadTopZones(params) {
    const query = new URLSearchParams(params);
    query.set("by", "pickup");
    query.set("limit", "5");
    const rows = await fetchJSON(`/api/charts/top-zones?${query}`);
    const maximum = Math.max(1, ...rows.map(row => Number(row.trips)));
    rankingList.innerHTML = rows.length ? rows.map((row, index) => `
        <div class="ranking-item">
            <div class="rank-number">${String(index + 1).padStart(2, "0")}</div>
            <div class="rank-details">
                <div class="rank-title">
                    <strong>${escapeHTML(row.zone_name)}</strong>
                    <span>${Number(row.trips).toLocaleString()}</span>
                </div>
                <div class="progress-track">
                    <div class="progress-value" style="width: ${Number(row.trips) / maximum * 100}%"></div>
                </div>
            </div>
        </div>`).join("") : "<p>No pickup data available.</p>";
}

function renderBarList(container, rows, labelKey) {
    const maximum = Math.max(1, ...rows.map(row => Number(row.trips)));
    container.innerHTML = rows.length ? rows.map(row => `
        <div class="borough-row">
            <span>${escapeHTML(row[labelKey])}</span>
            <div class="borough-bar">
                <div style="width: ${Number(row.trips) / maximum * 100}%"></div>
            </div>
            <strong>${Number(row.trips).toLocaleString()}</strong>
        </div>`).join("") : "<p>No trips match these filters.</p>";
}

async function loadBoroughs(params) {
    const rows = await fetchJSON(`/api/charts/boroughs?${params}`);
    renderBarList(boroughList, rows, "borough");
}

async function loadDistanceDistribution(params) {
    const rows = await fetchJSON(`/api/charts/distance-distribution?${params}`);
    renderBarList(document.getElementById("distanceDistribution"), rows, "bucket");
}


const tripTrendChart = document.getElementById("tripTrendChart");

async function loadDailyTrend(params){
    const query = params.toString();
    const rows = await fetchJSON(
        query
            ? `/api/charts/daily?${query}`
            : "/api/charts/daily"
    );

    renderLineChart(rows);

}

function renderLineChart(rows) {
    if (!rows.length) {

        tripTrendChart.innerHTML =
         "<p>No trend data available.</p>";

         return;

    }

    const width = 900;
    const height = 250;
    const padding = 25;

    const maxTrips =
        Math.max(
            ...rows.map(
                row =>
                    Number(
                        row.trips
                    )
            )
        );

    const points =
        rows.map(
            function (row,index) {

                const x =
                    padding +
                    (
                        index /
                        Math.max(
                            rows.length - 1,
                            1
                        )
                    ) *
                    (
                        width -
                        padding * 2
                    );


                const y =
                    height -
                    padding -
                    (
                        Number(
                            row.trips
                        ) /
                        (maxTrips || 1)
                    ) *
                    (
                        height -
                        padding * 2
                    );


                return {
                    x,
                    y
                };

            }
        );


    const linePoints =
        points
            .map(point => `${point.x},${point.y}`).join(" ");


    tripTrendChart.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">

            <polyline
                points="${linePoints}"
                fill="none"
                stroke="var(--primary-dark)"
                stroke-width="3"
                stroke-linecap="round"
                stroke-linejoin="round"
            ></polyline>

            ${
                points
                    .map(
                        point => `
                            <circle
                                cx="${point.x}"
                                cy="${point.y}"
                                r="4"
                                fill="white"
                                stroke="var(--primary-dark)"
                                stroke-width="2"
                            ></circle>
                        `
                    )
                    .join("")
            }

        </svg>
    `;


}

async function loadFilterOptions() {

    const data =
        await fetchJSON(
            "/api/filters"
        );


    pickupFilter.innerHTML = `
        <option value="">
            All Locations
        </option>
    `;


    data.boroughs.forEach(
        function (borough) {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                borough;

            option.textContent =
                borough;

            pickupFilter.appendChild(
                option
            );

        }
    );


    if (data.min_date) {

        dateFilter.min =
            String(
                data.min_date
            ).slice(
                0,
                10
            );

    }


    if (data.max_date) {

        dateFilter.max =
            String(
                data.max_date
            ).slice(
                0,
                10
            );

    }

}

async function loadDashboard() {

    const params =
        buildFilterParams();


    applyFiltersButton.disabled =
        true;

    applyFiltersButton.textContent =
        "Loading...";


    try {

        await Promise.all([

            loadSummary(params),

            loadTrips(params),

            loadDailyTrend(params),

            loadTopZones(params),

            loadBoroughs(params),

            loadDistanceDistribution(params)

        ]);


    } catch (error) {

        console.error(
            error
        );


        alert(
            "Dashboard data could not be loaded. Check Flask and MySQL."
        );


    } finally {

        applyFiltersButton.disabled =
            false;

        applyFiltersButton.textContent =
            "Apply Filters";

    }
}

applyFiltersButton.addEventListener(
    "click",
    loadDashboard
);

resetFiltersButton.addEventListener(
    "click",
    function () {

        dateFilter.value = "";

        pickupFilter.value = "";

        distanceFilter.value = "";

        fareFilter.value = "";


        loadDashboard();

    }
);



//DETAIL DRAWER
const detailDrawer = document.getElementById("detailDrawer");
const drawerBackdrop = document.getElementById("drawerBackdrop");
const drawerClose = document.getElementById("drawerClose");

const drawerTitle = document.getElementById("drawerTitle");
const drawerContent = document.getElementById("drawerContent");

function openDrawer(title, content, eyebrow = "TRIP DETAILS") {
    drawerTitle.textContent = title;
    drawerContent.innerHTML = content;
    detailDrawer.querySelector(".drawer-eyebrow").textContent = eyebrow;
    detailDrawer.classList.add("open");
    drawerBackdrop.classList.add("open");
    detailDrawer.setAttribute("aria-hidden", "false");
    closeMobileSidebar();
    drawerClose.focus();
}

function closeDrawer() {
    detailDrawer.classList.remove("open");
    drawerBackdrop.classList.remove("open");
    detailDrawer.setAttribute("aria-hidden", "true");
}

drawerClose.addEventListener("click", closeDrawer);
drawerBackdrop.addEventListener("click", closeDrawer);

document.querySelector('[data-drawer="about"]').addEventListener("click", () => {
    openDrawer("Urban Mobility Intelligence", `
        <p>Urban Mobility Intelligence is a full-stack analytics dashboard for exploring patterns in New York City Yellow Taxi trip data.</p>
        <div class="drawer-section">
            <h4>Dataset</h4>
            <p>NYC Taxi &amp; Limousine Commission Yellow Taxi Trip Records</p>
        </div>
        <div class="drawer-section">
            <h4>Stack</h4>
            <p>Python data pipeline<br>MySQL<br>Flask API<br>HTML / CSS / JavaScript</p>
        </div>`, "ABOUT");
});

async function loadTripDetail(tripId) {
    try {
        const trip = await fetchJSON(`/api/trips/${encodeURIComponent(tripId)}`);
        const fields = [
            ["Pickup zone", trip.pickup_zone],
            ["Dropoff zone", trip.dropoff_zone],
            ["Distance", `${Number(trip.trip_distance).toFixed(1)} mi`],
            ["Duration", `${Number(trip.duration_min).toFixed(1)} min`],
            ["Fare", `$${Number(trip.total_amount).toFixed(2)}`],
            ["Payment type", trip.payment_type],
            ["Passenger count", trip.passenger_count]
        ];
        openDrawer(`${trip.pickup_zone} → ${trip.dropoff_zone}`,
            `<div class="detail-grid">${fields.map(([label, value]) => `
                <div class="detail-stat"><span>${label}</span><strong>${escapeHTML(value)}</strong></div>
            `).join("")}</div>`);
    } catch (error) {
        console.error(error);
        alert("Trip details could not be loaded. Please try again.");
    }
}

document.getElementById("exportButton").addEventListener("click", () => {
    const rows = [["Pickup", "Dropoff", "Distance", "Duration", "Fare"]];
    tripTablebody.querySelectorAll(".trip-row").forEach(row => {
        rows.push(Array.from(row.cells).slice(0, 5).map(cell => cell.textContent.trim()));
    });
    const csv = rows.map(row => row.map(value =>
        `"${String(value).replace(/"/g, '""')}"`).join(",")).join("\r\n");
    const url = URL.createObjectURL(new Blob([csv], {type: "text/csv;charset=utf-8"}));
    const link = document.createElement("a");
    link.href = url;
    link.download = "urban-mobility-trips.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    closeMobileSidebar();
});

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



// Highlight the current top navigation section.
const navigationItems = document.querySelectorAll(".top-nav-item");

function updateActiveNavigation() {
    const section = window.location.hash || "#overview";
    navigationItems.forEach(item => {
        const active = item.getAttribute("href") === section;
        item.classList.toggle("active", active);
        if (active) item.setAttribute("aria-current", "location");
        else item.removeAttribute("aria-current");
    });
}

navigationItems.forEach(item => {
    item.addEventListener("click", () => closeMobileSidebar());
});
window.addEventListener("hashchange", updateActiveNavigation);
updateActiveNavigation();


// INITAL APP STATE
async function initialiseApp() {

    try {

        await loadFilterOptions();

        await loadDashboard();


        console.log(
            "Urban Mobility Intelligence ready."
        );


    } catch (error) {

        console.error(
            "Application startup failed:",
            error
        );
        alert("Dashboard data could not be loaded. Check Flask and MySQL.");

    }
}


initialiseApp();
