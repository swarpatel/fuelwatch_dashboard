# WA FuelWatch Interactive Dashboard ⛽

A responsive, real-time dashboard for visualizing and filtering Western Australia fuel prices, powered by the official FuelWatch RSS feed. Built with Streamlit and Folium, packaged in a lightweight Docker container.

## ✨ Features

* **Real-Time Data:** Fetches the latest fuel prices directly from the WA FuelWatch API.
* **Smart Filtering:**
  * Filter by Fuel Type (ULP, PULP, Diesel) and Brand.
  * Filter by Region (North of River, South of River, or All Metro) natively via the API.
  * **Radius Search:** Enter a ZIP code to automatically filter stations within a 5KM, 10KM, or 20KM radius.
* **Interactive Data Table:** * Sortable list of the cheapest fuel stations.
  * *Click-to-View:* Select a row's checkbox to instantly view the station's details and zoom the map to its exact location.
* **Dynamic Map Integration:**
  * Auto-zooms based on your search context (overall view, ZIP code level, or specific station level).
  * Highlights selected stations in red.
* **Quick Actions:**
  * 1-click "Copy to Clipboard" for station addresses.
  * Direct links to open the selected station in Google Maps for navigation.
* **Mobile & Full-Screen Ready:** Custom UI styling removes default padding and menus for a seamless, app-like experience on any device.

---

## 🚀 Getting Started (Docker)

The application is fully containerized, meaning you don't need to install Python or any dependencies on your host machine.

### Prerequisites
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
* [Git](https://git-scm.com/) installed.

### 1. Clone the Repository
Open your terminal or command prompt and clone the project:
`bash
git clone https://github.com/swarpatel/fuelwatch_dashboard.git
cd fuelwatch_dashboard
`

### 2. Build the Docker Image
Run the following command in the directory containing the `Dockerfile`:
`bash
docker build -t fuel-dash .
`

### 3. Run the Container
Start the container and bind it to your local machine for secure access:
`bash
docker run -d -p 127.0.0.1:8501:8501 --name my-fuel-dash fuel-dash
`
*Note: Binding to `127.0.0.1` ensures the dashboard is only accessible from your local machine, adding a layer of security.*

### 4. Access the Dashboard
Open your web browser and navigate to:
👉 **[http://localhost:8501](http://localhost:8501)**

---

## 🛠️ Development & Live Reloading

If you want to modify the code (`app.py`) and see changes instantly without rebuilding the Docker image, run the container with a volume mount:

**Windows (Command Prompt):**
`cmd
docker run -p 127.0.0.1:8501:8501 -v "%cd%":/app fuel-dash
`

**Mac/Linux/PowerShell:**
`bash
docker run -p 127.0.0.1:8501:8501 -v "${PWD}":/app fuel-dash
`
Save your changes in your code editor, and Streamlit will automatically prompt you to rerun the app in the browser.

## 🛑 Stopping the Application
To stop the running container:
`bash
docker stop my-fuel-dash
docker rm my-fuel-dash
`