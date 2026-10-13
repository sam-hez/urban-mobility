# Urban Mobility Data Explorer - UI Plan

## 1. Purpose

The Urban Mobility Data Explorer dashaboard provdes an easy way for users to explore patterns in New York City taxi trips. The interface will allow users to understand mobility behavior through summary statistics, visualizations, filters, and trip-level records.

The frontend is initially being developed using placeholder data. The placeholder values will later be replace with data returned by the backend flask API 

---

## 2. Important Dataset Fields 

The dashboard is designed around important field from the NYC Yellow Taxi dataset.

### Time
- Pickup datetime
- Dropoff datetime

### Location 
- Pickup Location ID 
- Dropoff Location ID

### Trip Information
- Trip Distance
- Passenger count
- Trip duration

### Fare Information
- Fare amount
- Tip amount
- Total amound
- Payment type

---

## 3. Dashboard Information Heirarchy

The dashboard follows this information heirarchy:

1. Dashboard title and context
2. Global filters
3. Key performance indicators
4. Mobility trends
5. Geographic movement
6. Fare and distance analysis
7. Recent trip records

This structure allwos users to mvoe from heigh level information to detailed trip level information

---

## 4. Dashboard KPI Cards

Initial KPI cards

- Total Trips 
- Average Trip Distance
- Average Fare
- Average Trip Duration

Additional metric may be added later depending on insiughts discovered during the data analysis by devis

---

## 5. Planned Visualizations

### Trips Over Time
A line chart showing how the number of taxi trips changes over time.

Purpose: 
Idenify peak and low demand periods.

### Popular Pickup Locations
A ranked visualization showing the zones with the highest number of pickups

Purpose: 
Identify major mobility hotspots.

### Fare vs Distance 
A visualization comparing trip distance and fare amount.

Purpose: 
Explore the relationship between trip lenght and trip cost 

### Borough Distribution
A visualization show the distribution of trips across NYC boroughs.

Purpose: 
Understand the geographic patterns in taxi activity

---

## 6. Filters

The dashboard will support:

- Date 
- Pickup location
- Dropoff location
- Distance Range
- Fare range

Filter will later send query paramenters to the Flask API
such as: 
GET /api/trips?pickup_zone=Manhattan&min_distance=2&max_distance=10


---

## 7. Responsive Design

The dashboard will support:

- Desktop
- Tablet 
- Mobile

## 8. Design Principles

- Simple
- Professional
- Responsible
- Data focus
- Easy to scan
- Consistent 
- Suitable for analytic storytelling



## 9. API Integration Strategy

The frontend currently uses temporary placeholder values

